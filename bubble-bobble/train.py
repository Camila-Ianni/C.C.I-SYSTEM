from common.env.subproc_vec_env import SubprocVecEnv
from common.env.atari_wrappers import wrap_deepmind, TransposeFrame
from common.logger import Logger
from common.storage import Storage
from common.model import MlpModel, NatureModel, ImpalaModel
from common.policy import CategoricalPolicy, DiagGaussianPolicy
from common import set_global_seeds, set_global_log_levels

import os, time, yaml, argparse
import gym, retro
import random
import torch


def create_agent(exp_name, env_name, hyperparameters, device, seed, num_checkpoints):
    # Choose the 'cuda' or 'cpu' device
    if device == 'cpu':
        device = torch.device("cpu")
    elif device == 'gpu':
        device = torch.device('cuda')

    #################
    ## Environment ##
    #################
    def create_env(env_name, n_envs):
        # Different from atari environment, environment could not be pickled
        # Therefore, environment should be initialized separately in subprocess
        class EnvFnWrapper():
            def __init__(self, env_name):
                self.env_name = env_name

            def __call__(self, *args, **kwargs):
                env = retro.make(self.env_name, use_restricted_actions=retro.Actions.DISCRETE)
                env = wrap_deepmind(env)
                return env

        env_fn = EnvFnWrapper(env_name)
        env = SubprocVecEnv(n_envs, env_fn)
        return env

    print('INITIALIZAING ENVIRONMENTS...')
    n_steps = hyperparameters.get('n_steps', 5)
    n_envs = hyperparameters.get('n_envs', 16)
    env = create_env(env_name, n_envs)
    print('DONE!')

    ######################
    ## Logger & STORAGE ##
    ######################
    def create_logger(exp_name, env_name, n_envs, seed):
        logdir = env_name + '/' + '/' + exp_name + '/' + 'seed' + '_' + str(seed)  + '_' + time.strftime("%d-%m-%Y_%H-%M-%S")
        logdir = os.path.join('logs', logdir)
        if not(os.path.exists(logdir)):
            os.makedirs(logdir)
        return Logger(n_envs, logdir)

    def create_stroage(env, n_steps, n_envs, device):
        observation_space = env.observation_space
        observation_shape = observation_space.shape
        return Storage(observation_shape, n_steps, n_envs, device)

    print('INITIALIZAING LOGGER & STORAGE...')
    logger = create_logger(exp_name, env_name, n_envs, seed)
    with open(logger.logdir + '/config.yml', 'w') as f:
        yaml.dump(hyperparameters, f)
    storage = create_stroage(env, n_steps, n_envs, device)
    print('DONE!')

    ###########
    ## Model ##
    ###########
    def create_model(env, architecture='nature'):
        observation_space = env.observation_space
        observation_shape = observation_space.shape

        if architecture == 'nature':
            return NatureModel(in_channels=observation_shape[0])
        elif architecture == 'impala':
            return ImpalaModel(in_channels=observation_shape[0])
    
    def create_policy(env, model):
        # Build policy with the corresponding action space
        action_space = env.action_space

        # Discrete action space
        if isinstance(action_space, gym.spaces.Discrete):
            action_size = action_space.n
            policy = CategoricalPolicy(model, action_size)

        # Continuous action space
        elif isinstance(action_space, gym.spaces.Box):
            action_size = action_space.shape[0]
            low = action_space.low[0]
            high = action_space.high[0]
            policy = DiagGaussianPolicy(model, action_size, (low, high))

        else: 
            raise NotImplementedError
        return policy

    print('INITIALIZAING MODEL...')
    architecture = hyperparameters.get('architecture', 'nature')
    model = create_model(env, architecture)
    policy = create_policy(env, model)
    policy.to(device)
    print('DONE!')
    ###########
    ## AGENT ##
    ###########
    algo = hyperparameters.get('algo', 'ppo')
    if algo == 'ppo':
        from agents.ppo import PPO as AGENT
    else:
        raise NotImplementedError

    return AGENT(env, policy, logger, storage, device, num_checkpoints, **hyperparameters)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--exp_name',       type=str, default = 'test', help='experiment name')
    parser.add_argument('--env_name',       type=str, default = 'BubbleBobble-Nes', help='environment ID')
    parser.add_argument('--param_name',     type=str, default = 'baseline', help='hyper-parameter ID')
    parser.add_argument('--device',         type=str, default = 'gpu', required = False, help='whether to use gpu')
    parser.add_argument('--gpu_device',     type=int, default = int(0), required = False, help = 'visible device in CUDA')
    parser.add_argument('--num_timesteps',  type=int, default = int(100000000), help = 'overwrite the number of training timesteps')
    parser.add_argument('--seed',           type=int, default = random.randint(0,9999), help='Random generator seed')
    parser.add_argument('--log_level',      type=int, default = int(40), help='[10,20,30,40]')
    parser.add_argument('--num_checkpoints',type=int, default = int(10), help='number of checkpoints to store')

    args = parser.parse_args()
    exp_name = args.exp_name
    env_name = args.env_name
    param_name = args.param_name
    device = args.device
    gpu_device = args.gpu_device
    num_timesteps = args.num_timesteps
    seed = args.seed
    log_level = args.log_level
    num_checkpoints = args.num_checkpoints
    set_global_seeds(seed)
    set_global_log_levels(log_level)

    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_device)
    ##############
    ## Training ##
    ##############
    print('LOADING HYPERPARAMETERS...')
    with open('./hyperparams/config.yml', 'r') as f:
        hyperparameters = yaml.safe_load(f)[param_name]
    for key, value in hyperparameters.items():
        print(key, ':', value)
    print('DONE!')
    agent = create_agent(exp_name, env_name, hyperparameters, device, seed, num_checkpoints)
    print('START TRAINING...')
    agent.train(num_timesteps)
    print('DONE!')