from common.env.atari_wrappers import wrap_deepmind
from common.model import MlpModel, NatureModel, ImpalaModel
from common.policy import CategoricalPolicy
from common import set_global_seeds

import numpy as np
import pygame, cv2
import os, time, yaml, argparse, random
import retro
import torch

def display_arr(screen, arr, video_size, transpose):
    arr_min, arr_max = arr.min(), arr.max()
    arr = 255.0 * (arr - arr_min) / (arr_max - arr_min)
    pyg_img = pygame.surfarray.make_surface(arr.swapaxes(0, 1) if transpose else arr)
    pyg_img = pygame.transform.scale(pyg_img, video_size)
    screen.blit(pyg_img, (0, 0))
    return pygame.surfarray.array3d(pyg_img)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env_name', type=str, default = 'BubbleBobble-Nes', help='environment ID')
    parser.add_argument('--log_path', type=str, default='./logs/BubbleBobble-Nes/baseline')
    parser.add_argument('--checkpoint', type=str, default='100000000', help='model checkpoint to load')
    parser.add_argument('--device',  type=str, default = 'gpu', required = False, help='whether to use gpu')
    parser.add_argument('--seed', type=int, default = random.randint(0,9999), help='Random generator seed')

    args = parser.parse_args()
    env_name = args.env_name
    log_path = args.log_path
    checkpoint = args.checkpoint
    device = args.device
    seed = args.seed
    model_path = log_path + '/model_' + checkpoint + '.pth'
    set_global_seeds(seed)

    with open(log_path + '/config.yml', 'r') as f:
        hyperparameters = yaml.safe_load(f)

    # Designate device
    if device == 'cpu':
        device = torch.device("cpu")
    elif device == 'gpu':
        device = torch.device('cuda')

    # Initialize Environment
    env = retro.make(env_name, use_restricted_actions=retro.Actions.DISCRETE)
    env = wrap_deepmind(env)
    env.seed(seed)

    # Initialize Model
    observation_space = env.observation_space
    observation_shape = observation_space.shape
    action_space = env.action_space
    action_size = action_space.n
    architecture = hyperparameters.get('architecture', 'nature')
    if architecture == 'nature':
        embedder = NatureModel(in_channels=observation_shape[0])
    elif architecture == 'impala':
        embedder = ImpalaModel(in_channels=observation_shape[0])
    policy = CategoricalPolicy(embedder, action_size)
    saved_model = torch.load(model_path)
    policy.load_state_dict(saved_model['state_dict'])
    policy.to(device)
    policy.eval()

    #Initialize Agent
    if hyperparameters['algo'] == 'ppo':
        from agents.ppo import PPO as AGENT
    else:
        raise NotImplementedError
    agent = AGENT(env, policy, None, None, device, 0, **hyperparameters)

    # Pygame Configurations
    zoom = 4
    fps = 40
    transpose = True
    rendered = env.render(mode='rgb_array')
    video_size = [rendered.shape[1], rendered.shape[0]]
    video_size = int(video_size[0] * zoom), int(video_size[1] * zoom)
    screen = pygame.display.set_mode(video_size)
    clock = pygame.time.Clock()

    # Evaluation
    obs = env.reset()
    total_rewards = 0
    images = []
    while True:
        obs = torch.FloatTensor(obs).unsqueeze(0).to(device=device)
        act = policy.action(obs)
        next_obs, rew, done, info = env.step(act)
        obs = next_obs
        total_rewards += rew

        if obs is not None:
            rendered = env.render(mode='rgb_array')
            image = display_arr(screen, rendered, transpose=transpose, video_size=video_size)
            images.append(image)

        pygame.display.flip()
        clock.tick(fps)
        if info['lives'] == 0:
            break

    # Write video
    out = cv2.VideoWriter('project.avi', cv2.VideoWriter_fourcc(*'DIVX'), 30, video_size, True)
    for image in images:
        image = np.transpose(image, (1,0,2))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        out.write(image)
    out.release()