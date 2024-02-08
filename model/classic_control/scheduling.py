"""
Classic cart-pole system implemented by Rich Sutton et al.
Copied from http://incompleteideas.net/sutton/book/code/pole.c
permalink: https://perma.cc/C9ZM-652R
"""
import sys
sys.path.append('/etc/kubernetes') 
import math
from typing import Optional, Tuple, Union
import numpy as np
import gymnasium as gym
from gymnasium import logger, spaces
from model.main import node_count, get_nodes_network_usage, setSuggestion




class SchedulingEnv(gym.Env[np.ndarray, Union[int, np.ndarray]]):

    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_fps": 50,
    }

    def __init__(self, render_mode: Optional[str] = None):

        #GOAL: the agent must choose the node that has the lower network_usage to schedule a new pod
        #OBSERVATION : provides the actual usage of network from nodes 
        #ACTIONS: possible actions are n_nodes +1 that is dontschedule action
        #REWARD: the reward is 1 when the choosed node has memory usage that is the lower between possible usages
        #STATE: mem usages
        #self.memory_usage_metrics = None
        #self.memory_capacity_metrics = None
        #self.cpu_usage_metrics = None
        #self.cpu_capacity_metrics = None

        self.num_of_nodes = None
        self.min_usage = np.zeros(node_count()-1, dtype=np.float32)
        self.max_usage = np.full(node_count()-1, float('inf'), dtype=np.float32)
        self.network_usage_metrics = None

        #da aggiungere le informazioni sulle risorse richieste dal pod da schedulare

        self.num_of_actions = None
        self.action_space = spaces.Discrete(node_count()+ 1)
        self.observation_space = spaces.Box(self.min_usage, self.max_usage,  dtype=np.float32) #values of memory usage in range [min_usage, max_usage]
        
        self.usage_treshold = 1
        self.steps_beyond_terminated = None
        self.screen = None

        self.reset()



    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ):
        super().reset(seed=seed)
        # Note that if you use custom reset bounds, it may lead to out-of-bound
        # state/observations.
        print(self.max_usage)
        self.state = get_nodes_network_usage(["172.19.0.4", "172.19.0.3", "172.19.0.5"])
        print(f"RESET STATE: {self.state}")

        self.num_of_nodes = node_count()
        self.network_usage_metrics = get_nodes_network_usage(["172.19.0.4", "172.19.0.3", "172.19.0.5"])
        self.num_of_actions = node_count() + 1

        return np.array(self.state, dtype=np.float32), {}

    def step(self, action):
        assert self.action_space.contains(
            action
        ), f"{action!r} ({type(action)}) invalid"
        assert self.state is not None, "Call reset before using step method."
        
        #########
        #APPLICARE L'ACTION SUL CLUSTER REALE TIPO schedule_on_node(action)
        #########

        print(f"ACTION: {action}")

        #aggiornare lo stato
        old_state = self.state
        self.state = get_nodes_network_usage(["172.19.0.4", "172.19.0.3", "172.19.0.5"])
        print(f"NEW STATE: {self.state}")

        #verifico se il nodo scelto era quello giusto:   
        node_to_select = -1  # Inizializza l'indice del nodo selezionato a -1 (nessun nodo selezionato)
        min_memory_usage = float('inf')     

        for i, node in enumerate(self.state):  
            network_usage = node
            if network_usage < min_memory_usage:
                min_memory_usage = network_usage
                node_to_select = i

        if node_to_select != -1:
            print(f"action: {action}   node_to_select: {node_to_select +1}")
            terminated = action.__eq__(node_to_select + 1)
            
        else:
            print("Nessun nodo con memory usage inferiore alla soglia")

        reward = 1 if terminated else 0  # Binary sparse rewards
        print(f"TERMINATED: {terminated}")

        agent_suggestions = {}

        if terminated:
            node_names= ["172.19.0.4", "172.19.0.3", "172.19.0.5"]
            for i, node_name in enumerate(node_names):
                if i == (action - 1):
                    agent_suggestions[node_name] = 10
                else:
                    agent_suggestions[node_name] = 1

            print(f"REWARD: {reward}")
            print(f"agent_suggestions: {agent_suggestions}")
            setSuggestion(agent_suggestions)

        
        return np.array(self.state, dtype=np.float32), reward, terminated, False, {}

    

    def close(self):
        if self.screen is not None:
            import pygame
            pygame.display.quit()
            pygame.quit()
            self.isopen = False
