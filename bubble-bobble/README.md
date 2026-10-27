Bubble-Bobble with Proximal Policy Optimization
===============

## Introduction

This repository contains code to train agent in Bubble-Bobble with several implementation tricks and modifications applied into Proximal Policy Optimization algorithm. 
It also supports to evaluate the model with visual display.

After training the agent with 100M frames, agent can easily solve the stages upto 13.

![](bubble_bobble.gif)

Papers related to this implementation are: <br>

[1] [PPO: Human-level control through deep reinforcement learning ](https://arxiv.org/abs/1707.06347) <br>
[2] [GAE: High-Dimensional Continuous Control Using Generalized Advantage Estimation ](https://arxiv.org/abs/1506.02438) <br>
[3] [IMPALA: Scalable Distributed Deep-RL with Importance Weighted Actor-Learner Architectures](https://arxiv.org/abs/1802.01561) (model architecture) <br>
[4] [RAD: Reinforcement Learning with Augmented Data](https://arxiv.org/abs/2004.14990) (random translate) <br>
[5] [Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO](https://arxiv.org/abs/2005.12729) <br>


## Requirements

- python 3.7
- torch 1.3
- gym-retro 0.8
- pygame 1.9


## Training

Use `train.py` to train the agent in Bubble-Bobble. It has the following arguments:
- `--exp_name`: ID to designate your expriment.
- `--env_name`: Environment ID used in gym.retro. 
- `--param_name`: Configurations name for your training. By default, the training loads hyperparameters from `hyperparams.config.yml/baseline`.
- `--num_timesteps`: Number of total timesteps to train your agent.

After you start training your agent, log and parameters are automatically stored in `logs/env-name/exp-name/`.

## Evaluation

Use `evaluate.py` to evaluate your trained agent. It has the following arguments:
- `--env_name`: Environment ID used in gym.retro. 
- `--log_path`: Path of the model's directory to evaluate. 
- `--checkpoint`: Model checkpoint to load. 

## Findings
- Following the common preprocessing procedures for `atari` were highly effective.
- Most of the implemettation tricks introduced in *Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO* were helpful. Especially value function clipping, orthogonal initialization, and learning rate annealing.  
- `Impala` architecture was able to learn much general feature than `Nature` architecture.
- `Random translation` from *RAD* accelerate the peformance by small margin while `Color jittering` degraded the performance.
- Use of `GAE` always helps to stabilize the performance.
