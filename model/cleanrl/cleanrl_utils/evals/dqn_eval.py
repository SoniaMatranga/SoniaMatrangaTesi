import random
from typing import Callable

import gymnasium as gym
import numpy as np
import torch


def evaluate(
    model_path: str,
    make_env: Callable,
    env_id: str,
    eval_episodes: int,
    run_name: str,
    Model: torch.nn.Module,
    device: torch.device = torch.device("cpu"),
    epsilon: float = 0.05,
    capture_video: bool = False,
):
    envs = gym.vector.SyncVectorEnv([make_env(env_id, 0, 0, capture_video, run_name)])
    model = Model(envs).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    obs, _ = envs.reset()
    episodic_returns = []
    while len(episodic_returns) < eval_episodes:
        action_masks = []
        for env_idx in range(envs.num_envs):
            env = envs.envs[env_idx]
            if hasattr(env, 'action_masks') and callable(getattr(env, 'action_masks')):
                action_mask = env.action_masks()
                action_masks.append(action_mask)
            else:
                action_masks.append(None) 
            action_mask = action_masks[0]

        action_mask_matrix = action_mask.reshape(1, -1) 
        if random.random() < epsilon:
            actions = []
            for env_mask in action_mask_matrix:
                valid_actions = np.where(env_mask)[0]
                actions = np.array([np.random.choice(valid_actions) for _ in range(envs.num_envs)])           
            #actions = np.array([envs.single_action_space.sample() for _ in range(envs.num_envs)])
        else:
            #q_values = model(torch.Tensor(obs).to(device))
            #actions = torch.argmax(q_values, dim=1).cpu().numpy()
            actions = model.predict(obs, action_mask_matrix) 
            
        next_obs, _, _, _, infos = envs.step(actions)
        if "final_info" in infos:
            for info in infos["final_info"]:
                if "episode" not in info:
                    continue
                print(f"eval_episode={len(episodic_returns)}, episodic_return={info['episode']['r']}")
                episodic_returns += [info["episode"]["r"]]
        obs = next_obs

    return episodic_returns


if __name__ == "__main__":
    from huggingface_hub import hf_hub_download

    from cleanrl.dqn import QNetwork, make_env

    model_path = hf_hub_download(repo_id="cleanrl/CartPole-v1-dqn-seed1", filename="q_network.pth")
    evaluate(
        model_path,
        make_env,
        "CartPole-v1",
        eval_episodes=10,
        run_name=f"eval",
        Model=QNetwork,
        device="cpu",
        capture_video=False,
    )
