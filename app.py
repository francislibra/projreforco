import os
import pygame
import math
import numpy as np
import random
import time
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

def run_server():
    server = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
    server.serve_forever()

thread = threading.Thread(target=run_server)
thread.daemon = True
thread.start()

class ResourceCollector:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

         # Carrega o som de recompensa
        try:
            sound_file = os.path.join("sounds", "coin-collect.wav")  # Ajuste o caminho conforme necessário
            self.collect_sound = pygame.mixer.Sound(sound_file)
            self.collect_sound.set_volume(0.3)  # Ajusta o volume para 30%
        except:
            print("Não foi possível carregar o som de recompensa")
            self.collect_sound = None

        # Controle de caminho e recompensa
        self.current_positions = []
        self.optimal_positions = []
        self.showing_reward = False
        self.reward_start_time = 0
        self.reward_duration = 1.0

        # Controle de piscar do texto
        self.blink_timer = 0
        self.blink_interval = 500
        self.show_blink_text = True
        self.last_blink_time = pygame.time.get_ticks()
        
        # Estados e pontuações
        self.current_score = 0
        self.best_score = 0
        self.is_paused = False
        self.auto_continue = False 

        # Estatísticas
        self.total_resources_checked = 0
        self.best_path_resources = 0
        self.resources_positions = set()

        # Configuração da tela
        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h
        self.width = self.screen_width
        self.height = self.screen_height
        self.info_panel_width = int(self.width * 0.2)
        
        # Configuração do display
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption('Robô Coletor - Q-Learning')
        
        # Cálculo de tamanhos responsivos
        self.cell_size = min(int((self.width - self.info_panel_width) / 20), int(self.height / 20))
        self.robot_size = int(self.cell_size * 0.75)
        self.grid_width = (self.width - self.info_panel_width) // self.cell_size
        self.grid_height = self.height // self.cell_size
        
        # Configuração de fontes
        # Modifique o cálculo dos tamanhos de fonte
        self.base_font_size = int(min(self.width, self.height) * 0.02)
        self.large_font_size = int(self.base_font_size * 1.2)
        self.small_font_size = int(self.base_font_size * 0.8)
        self.position_font_size = int(self.base_font_size ) 
        
        # Crie as fontes
        self.input_font = pygame.font.Font(None, self.base_font_size)
        self.grid_font = pygame.font.Font(None, self.small_font_size)
        self.info_font = pygame.font.Font(None, self.base_font_size)
        self.position_font = pygame.font.Font(None, self.position_font_size) 
        
        # Configuração da caixa de entrada
        padding = int(self.info_panel_width * 0.05)
        input_width = self.info_panel_width - (padding * 2)
        self.input_box = pygame.Rect(
            self.width - self.info_panel_width + padding,
            padding,
            input_width,
            self.base_font_size + 10
        )
        
        # Inicialização de componentes
        self.robot_img = self.create_robot_image()
        self.reward_icon = self.create_reward_icon()
        self.input_text = ''
        self.input_active = False
        self.custom_resources = []
        self.can_start = False
        
        # Parâmetros do Q-Learning
        self.q_table = {}
        self.learning_rate = 0.1
        self.gamma = 0.9
        self.epsilon = 1.0
        self.min_epsilon = 0.01
        self.epsilon_decay = 0.995
        
        # Estados do jogo
        self.fixed_resources = []
        self.discovered_resources = []
        self.resource_order = []
        self.optimal_path = []
        self.best_path_found = False
        self.episode = 0
        self.current_path = []
        self.episode_start_time = time.time()
        self.best_moves = float('inf')
        self.results = []
        self.first_run_complete = False

        # Inicialização do monitor
        initial_data = {
            'best_moves': float('inf'),
            'episode': 0,
            'results': []
        }
        with open('resultados.json', 'w') as f:
            json.dump(initial_data, f)
        
        self.create_monitor_html()
        self.reset()

    def wrap_text(self, text, font, max_width):
        words = text.split(', ')
        lines = []
        current_line = []
        current_width = 0
        
        for word in words:
            word_surface = font.render(word + ', ', True, (0, 0, 0))
            word_width = word_surface.get_width()
            
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                if current_line:
                    lines.append(', '.join(current_line))
                current_line = [word]
                current_width = word_width
        
        if current_line:
            lines.append(', '.join(current_line))
        
        return lines

    def draw_position_box(self, info_surface, title, positions_text, y_pos):
        # Desenha o título
        title_surface = self.info_font.render(title, True, (0, 0, 0))
        info_surface.blit(title_surface, (10, y_pos))
        y_pos += self.base_font_size

        # Calcula a largura máxima disponível para o texto
        max_width = self.info_panel_width - 40
        
        # Se for o menor caminho, colorir as posições dos recursos
        if "menor caminho" in title:
            positions = positions_text.split(", ")
            colored_positions = []
            
            for pos_str in positions:
                # Converter string "(x,y)" em coordenadas
                x, y = map(int, pos_str.strip("()").split(","))
                pos = [x, y]
                
                # Verificar se a posição contém um recurso
                if pos in self.fixed_resources:
                    # Renderizar em vermelho
                    text_surface = self.position_font.render(pos_str, True, (255, 0, 0))
                else:
                    # Renderizar em preto
                    text_surface = self.position_font.render(pos_str, True, (0, 0, 0))
                
                colored_positions.append((text_surface, pos_str))
            
            # Organizar as posições em linhas
            lines = []
            current_line = []
            current_width = 0
            
            for text_surface, pos_str in colored_positions:
                width = text_surface.get_width() + self.position_font.size(", ")[0]
                
                if current_width + width <= max_width:
                    current_line.append((text_surface, pos_str))
                    current_width += width
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [(text_surface, pos_str)]
                    current_width = width
            
            if current_line:
                lines.append(current_line)
            
            # Calcular altura da caixa
            line_height = int(self.position_font_size * 1.2)
            box_height = (len(lines) + 1) * line_height
            
            # Desenhar a caixa
            box_rect = pygame.Rect(10, y_pos, self.info_panel_width - 20, box_height)
            pygame.draw.rect(info_surface, (255, 255, 255), box_rect)
            pygame.draw.rect(info_surface, (200, 200, 200), box_rect, 1)
            
            # Renderizar o texto colorido
            text_y = y_pos + 5
            for line in lines:
                text_x = 15
                for text_surface, pos_str in line:
                    info_surface.blit(text_surface, (text_x, text_y))
                    text_x += text_surface.get_width()
                    if pos_str != line[-1][1]:  # Se não for o último item da linha
                        comma_surface = self.position_font.render(", ", True, (0, 0, 0))
                        info_surface.blit(comma_surface, (text_x, text_y))
                        text_x += comma_surface.get_width()
                text_y += line_height
            
            return y_pos + box_height + 10
        else:
            # Comportamento original para outras caixas de texto
            lines = self.wrap_text(positions_text, self.position_font, max_width)
            line_height = int(self.position_font_size * 1.2)
            box_height = (len(lines) + 1) * line_height
            
            box_rect = pygame.Rect(10, y_pos, self.info_panel_width - 20, box_height)
            pygame.draw.rect(info_surface, (255, 255, 255), box_rect)
            pygame.draw.rect(info_surface, (200, 200, 200), box_rect, 1)

            text_y = y_pos + 5
            for line in lines:
                text_surface = self.position_font.render(line, True, (0, 0, 0))
                info_surface.blit(text_surface, (15, text_y))
                text_y += line_height
            
            return y_pos + box_height + 10

    def create_reward_icon(self):
            size = self.cell_size
            icon = pygame.Surface((size, size), pygame.SRCALPHA)
            
            color = (255, 215, 0)  # Dourado
            center = (size // 2, size // 2)
            radius = size // 3
            points = []
            
            for i in range(10):
                angle = math.pi/2 + (2 * math.pi * i) / 10
                r = radius * (0.5 if i % 2 else 1.0)
                points.append((
                    center[0] + r * math.cos(angle),
                    center[1] - r * math.sin(angle)
                ))
            
            pygame.draw.polygon(icon, color, points)
            return icon

    def create_robot_image(self):
        robot = pygame.Surface((self.robot_size, self.robot_size), pygame.SRCALPHA)
        
        body_size = int(self.robot_size * 0.67)
        body_offset = int((self.robot_size - body_size) / 2)
        eye_size = int(self.robot_size * 0.1)
        antenna_size = int(self.robot_size * 0.067)
        
        pygame.draw.rect(robot, (160, 160, 160),
                        (body_offset, body_offset, body_size, body_size),
                        border_radius=3)
        
        antenna_y = int(self.robot_size * 0.1)
        pygame.draw.circle(robot, (192, 192, 192),
                         (int(self.robot_size * 0.33), antenna_y), antenna_size)
        pygame.draw.circle(robot, (192, 192, 192),
                         (int(self.robot_size * 0.67), antenna_y), antenna_size)
        
        eye_y = int(self.robot_size * 0.4)
        pygame.draw.circle(robot, (0, 149, 255),
                         (int(self.robot_size * 0.37), eye_y), eye_size)
        pygame.draw.circle(robot, (0, 149, 255),
                         (int(self.robot_size * 0.63), eye_y), eye_size)
        
        highlight_size = int(eye_size * 0.3)
        pygame.draw.circle(robot, (255, 255, 255),
                         (int(self.robot_size * 0.37), eye_y - 1), highlight_size)
        pygame.draw.circle(robot, (255, 255, 255),
                         (int(self.robot_size * 0.63), eye_y - 1), highlight_size)
        
        mouth_y = int(self.robot_size * 0.6)
        for i in range(3):
            x_offset = int(self.robot_size * (0.33 + i * 0.17))
            pygame.draw.rect(robot, (80, 80, 80),
                           (x_offset, mouth_y,
                            int(self.robot_size * 0.067),
                            int(self.robot_size * 0.067)))
        
        return robot

    def render(self):
        self.screen.fill((255, 255, 255))
        # Draw grid
        grid_area_width = self.width - self.info_panel_width
        for x in range(0, grid_area_width, self.cell_size):
            pygame.draw.line(self.screen, (200, 200, 200),
                           (x, 0), (x, self.height))
            if x < grid_area_width - self.cell_size:
                num = self.grid_font.render(str(x // self.cell_size), True, (100, 100, 100))
                self.screen.blit(num, (x + self.cell_size//4, 5))
        
        for y in range(0, self.height, self.cell_size):
            pygame.draw.line(self.screen, (200, 200, 200),
                           (0, y), (grid_area_width, y))
            if y < self.height - self.cell_size:
                num = self.grid_font.render(str(y // self.cell_size), True, (100, 100, 100))
                self.screen.blit(num, (5, y + self.cell_size//4))
        

        # Draw optimal path
        if self.best_path_found:
            for i in range(len(self.optimal_path)-1):
                start_pos = (self.optimal_path[i][0] * self.cell_size + self.cell_size//2,
                           self.optimal_path[i][1] * self.cell_size + self.cell_size//2)
                end_pos = (self.optimal_path[i+1][0] * self.cell_size + self.cell_size//2,
                          self.optimal_path[i+1][1] * self.cell_size + self.cell_size//2)
                pygame.draw.line(self.screen, (255, 165, 0), start_pos, end_pos,
                               max(2, int(self.cell_size * 0.05)))
        
        # Draw resources
        for resource in self.custom_resources:
            self.draw_battery(resource)
        
        # Draw collected resources
        for resource in self.discovered_resources:
            if list(resource) not in self.resources:
                x = resource[0] * self.cell_size + int(self.cell_size * 0.125)
                y = resource[1] * self.cell_size + int(self.cell_size * 0.125)
                size = int(self.cell_size * 0.75)
                pygame.draw.rect(self.screen, (200, 200, 200), (x, y, size, size))
                pygame.draw.rect(self.screen, (150, 150, 150), (x, y, size, size), 2)

        # Draw reward icon
        if self.showing_reward:
            current_time = time.time()
            if current_time - self.reward_start_time < self.reward_duration:
                icon_pos = (
                    self.agent_pos[0] * self.cell_size,
                    self.agent_pos[1] * self.cell_size - self.cell_size
                )
                self.screen.blit(self.reward_icon, icon_pos)
                
                if current_time - self.reward_start_time < 0.2:
                    pygame.time.wait(100)
            else:
                self.showing_reward = False

        # Draw robot
        robot_pos = (self.agent_pos[0] * self.cell_size + (self.cell_size - self.robot_size)//2,
                    self.agent_pos[1] * self.cell_size + (self.cell_size - self.robot_size)//2)
        self.screen.blit(self.robot_img, robot_pos)
        
        # Update blink state
        current_time = pygame.time.get_ticks()
        if current_time - self.last_blink_time >= self.blink_interval:
            self.show_blink_text = not self.show_blink_text
            self.last_blink_time = current_time

        # Draw info panel
        info_surface = pygame.Surface((self.info_panel_width, self.height))
        info_surface.fill((240, 240, 240))
        
        # Draw input box
        pygame.draw.rect(info_surface,
                        (255,255,255) if self.input_active else (200,200,200),
                        pygame.Rect(10, 10, self.info_panel_width - 20, self.base_font_size + 10), 2)
        txt_surface = self.info_font.render(self.input_text, True, (0, 0, 0))
        info_surface.blit(txt_surface, (15, 15))

        # Instructions and status
        instructions = [
            "F5 - Reiniciar manual",
            "F6 - Reiniciar aleatório",
            "F10 - Continuar",
            f"Recursos Disponíveis: {len(self.custom_resources)}",
            "Digite linha,coluna",
            "Exemplo: 2,3",
            "ESC - Sair",
            "",
            "--- Estatísticas ---",
            f"Recompensas por Recurso: {self.current_score}",
            f"Recompensa Final: {self.best_score}",
            f"Total de Posições Verificadas: {len(self.resources_positions)}",
        ]
        
        # Render instructions
        y = self.base_font_size + 30
        line_height = int(self.base_font_size * 1.5)
        
        for instruction in instructions:
            if instruction.startswith("---"):
                text = self.info_font.render(instruction, True, (0, 100, 0))
            else:
                text = self.info_font.render(instruction, True, (0, 0, 0))
            info_surface.blit(text, (10, y))
            y += line_height

        y += line_height

        # Draw position boxes
        # all_positions_text = ", ".join([f"({x},{y})" for x, y in self.resources_positions])
        # y = self.draw_position_box(info_surface,
        #     "Posições verificadas (Todos os recursos):", 
        #     all_positions_text, 
        #     y
        # )

        if self.best_path_found:
            optimal_positions_text = ", ".join([f"({x},{y})" for x, y in self.optimal_path])
            y = self.draw_position_box(info_surface,
                "Posições verificadas (menor caminho):", 
                optimal_positions_text, 
                y
            )

            # Best path info
            best_path_info = [
                f"Recursos no menor caminho: {self.best_path_resources}",
                f"Total de posições no menor caminho: {self.best_moves}"
            ]
            
            for info in best_path_info:
                text = self.info_font.render(info, True, (0, 0, 0))
                info_surface.blit(text, (10, y))
                y += line_height

        # Status text
        if self.best_path_found and self.show_blink_text:
            text = self.info_font.render("Menor caminho encontrado!", True, (255, 0, 0))
            text_width = text.get_width()
            text_x = (self.info_panel_width - text_width) // 2
            info_surface.blit(text, (text_x, y))

        if len(self.custom_resources) == 5 and not self.can_start:
            text = self.info_font.render("Pronto para iniciar!", True, (0, 255, 0))
            text_width = text.get_width()
            text_x = (self.info_panel_width - text_width) // 2
            info_surface.blit(text, (text_x, y + line_height))

        self.screen.blit(info_surface, (self.width - self.info_panel_width, 0))
        pygame.display.flip()

    def draw_battery(self, pos):
            x = pos[0] * self.cell_size + int(self.cell_size * 0.125)
            y = pos[1] * self.cell_size + int(self.cell_size * 0.125)
            size = int(self.cell_size * 0.75)
            
            pygame.draw.rect(self.screen, (255, 255, 0), (x, y, size, size))
            pygame.draw.rect(self.screen, (0, 0, 0),
                            (x + size//2 - 2, y - 3, 4, 3))
            
            line_thickness = max(2, int(self.cell_size * 0.05))
            pygame.draw.line(self.screen, (0, 0, 0),
                            (x + size//4, y + size//2),
                            (x + 3*size//4, y + size//2), line_thickness)
            pygame.draw.line(self.screen, (0, 0, 0),
                            (x + size//2, y + size//4),
                            (x + size//2, y + 3*size//4), line_thickness)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                    
                if event.key == pygame.K_F5:
                    self.custom_resources = []
                    self.can_start = False
                    self.reset_game()
                    self.input_active = True
                    self.input_text = ''
                    self.is_paused = False
                    self.auto_continue = False
                
                elif event.key == pygame.K_F6:
                    self.custom_resources = []
                    for _ in range(5):
                        while True:
                            x = random.randint(0, self.grid_width - 1)
                            y = random.randint(0, self.grid_height - 1)
                            pos = [x, y]
                            if pos not in self.custom_resources:
                                self.custom_resources.append(pos)
                                break
                    self.fixed_resources = self.custom_resources.copy()
                    self.can_start = True
                    self.reset_game()
                    self.is_paused = False
                    self.auto_continue = False

                elif event.key == pygame.K_F10:
                    self.auto_continue = True
                    self.is_paused = False
                
                if self.input_active:
                    if event.key == pygame.K_RETURN:
                        self.process_input()
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif not (event.key in [pygame.K_F5, pygame.K_F6, pygame.K_F10, pygame.K_ESCAPE]):
                        self.input_text += event.unicode
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.input_box.collidepoint(event.pos):
                    self.input_active = True
                else:
                    self.input_active = False
        
        return True

    def get_state_key(self):
        resources_tuple = tuple(map(tuple, sorted(self.resources)))
        return (tuple(self.agent_pos), resources_tuple)

    def choose_action(self, state):
        if not self.first_run_complete:
            current_y = self.agent_pos[1]
            current_x = self.agent_pos[0]
            
            if len(self.discovered_resources) == len(self.fixed_resources):
                self.first_run_complete = True
                self.resource_order = sorted(self.discovered_resources, key=lambda r: (r[1], r[0]))
                return self.get_next_optimal_move()
                
            if current_x < self.grid_width - 1 and current_y % 2 == 0:
                return 1
            elif current_x > 0 and current_y % 2 == 1:
                return 3
            elif current_y < self.grid_height - 1:
                return 2
            else:
                return 0
        else:
            return self.get_next_optimal_move()

    def get_next_optimal_move(self):
        if not self.resources:
            return 0
            
        next_resource = None
        for resource in self.resource_order:
            if list(resource) in self.resources:
                next_resource = resource
                break
                
        if not next_resource:
            return 0
            
        if self.agent_pos[1] != next_resource[1]:
            return 2 if self.agent_pos[1] < next_resource[1] else 0
        
        if self.agent_pos[0] != next_resource[0]:
            return 1 if self.agent_pos[0] < next_resource[0] else 3
            
        return 0

    def step(self, action):
        if self.is_paused:
            return None, 0, True

        old_state = self.get_state_key()
        old_pos = self.agent_pos.copy()
        
        if action == 0:
            self.agent_pos[1] = max(0, self.agent_pos[1] - 1)
        elif action == 1:
            self.agent_pos[0] = min(self.grid_width - 1, self.agent_pos[0] + 1)
        elif action == 2:
            self.agent_pos[1] = min(self.grid_height - 1, self.agent_pos[1] + 1)
        elif action == 3:
            self.agent_pos[0] = max(0, self.agent_pos[0] - 1)
        
        moved = self.agent_pos != old_pos
        if moved:
            self.current_path.append(self.agent_pos.copy())
            self.resources_positions.add(tuple(self.agent_pos))
            self.total_resources_checked += 1
        
        reward = -1
        if self.agent_pos in self.resources:
            self.resources.remove(self.agent_pos)
            self.current_score += 10
            reward = 50

            # Toca o som de recompensa
            if hasattr(self, 'collect_sound') and self.collect_sound:
                self.collect_sound.play()

            self.showing_reward = True
            self.reward_start_time = time.time()

            if tuple(self.agent_pos) not in self.discovered_resources:
                self.discovered_resources.append(tuple(self.agent_pos))
                self.current_positions.append(self.agent_pos.copy())
                if len(self.discovered_resources) == len(self.fixed_resources):
                    self.resource_order = sorted(self.discovered_resources, key=lambda r: (r[1], r[0]))
        
        done = len(self.resources) == 0
        if done and not self.auto_continue:
            self.is_paused = True

        if done:
            if len(self.current_path) < self.best_moves:
                self.best_moves = len(self.current_path)
                self.optimal_path = self.current_path.copy()
                self.best_path_found = True
                self.best_path_resources = sum(1 for pos in self.optimal_path if list(pos) in self.fixed_resources)
                self.best_score = max(self.best_score, self.current_score)
            self.update_monitor()
        
        return old_state, reward, done

    def reset(self):
        self.current_score=0
        self.agent_pos = [0, 0]
        self.resources = [pos.copy() for pos in self.fixed_resources]
        self.current_path = [[0, 0]]
        return self.get_state_key()

    def reset_game(self):
        self.q_table = {}
        self.discovered_resources = []
        self.resource_order = []
        self.optimal_path = []
        self.best_path_found = False
        self.episode = 0
        self.current_path = []
        self.best_moves = float('inf')
        self.results = []
        self.first_run_complete = False
        
        self.current_score = 0
        self.total_resources_checked = 0
        self.best_path_resources = 0
        self.resources_positions = set()
        self.is_paused = False
        self.auto_continue = False

        if len(self.custom_resources) == 0:
            self.best_score = 0

        self.current_positions = []
        self.optimal_positions = []
        self.showing_reward = False
        
        self.reset()

    def process_input(self):
        try:
            line, col = map(int, self.input_text.strip().split(','))
            if 0 <= line < self.grid_height and 0 <= col < self.grid_width:
                pos = [col, line]
                if pos not in self.custom_resources and len(self.custom_resources) < 5:
                    self.custom_resources.append(pos)
                    self.can_start = False
                    if len(self.custom_resources) == 5:
                        self.fixed_resources = self.custom_resources.copy()
                        self.can_start = True
                        self.reset_game()
            self.input_text = ''
        except:
            self.input_text = ''

    def create_monitor_html(self):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Monitor de Resultados</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                tr:nth-child(even) { background-color: #f2f2f2; }
                tr.best { background-color: #dff0d8; }
                th { background-color: #4CAF50; color: white; }
            </style>
            <script>
                function updateResults() {
                    fetch('resultados.json')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('episode').textContent = data.episode;
                            document.getElementById('best-moves').textContent = data.best_moves;
                            
                            const tbody = document.getElementById('results-body');
                            tbody.innerHTML = '';
                            
                            data.results.forEach(result => {
                                const row = document.createElement('tr');
                                if (result.is_best) row.classList.add('best');
                                
                                row.innerHTML = `
                                    <td>${result.episode}</td>
                                    <td>${result.moves}</td>
                                    <td>${result.time}s</td>
                                    <td>${result.path}</td>
                                `;
                                
                                tbody.appendChild(row);
                            });
                        });
                }
                
                setInterval(updateResults, 1000);
                updateResults();
            </script>
        </head>
        <body>
            <h1>Monitor de Resultados</h1>
            <p>Episódio atual: <span id="episode">0</span></p>
            <p>Melhor número de movimentos: <span id="best-moves">∞</span></p>
            <table>
                <thead>
                    <tr>
                        <th>Episódio</th>
                        <th>Movimentos</th>
                        <th>Tempo</th>
                        <th>Caminho</th>
                    </tr>
                </thead>
                <tbody id="results-body">
                </tbody>
            </table>
        </body>
        </html>
        """
        
        with open('monitor_de_resultados.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

    def update_monitor(self):
        episode_time = time.time() - self.episode_start_time
        moves = len(self.current_path) - 1
        path_str = ' -> '.join([f'({x},{y})' for x, y in self.current_path])
        
        result = {
            'episode': self.episode,
            'moves': moves,
            'time': round(episode_time, 2),
            'path': path_str,
            'is_best': moves == self.best_moves,
            'current_score': self.current_score,
            'best_score': self.best_score,
            'positions_checked': self.total_resources_checked,
            'unique_positions': len(self.resources_positions),
            'resources_in_best_path': self.best_path_resources if self.best_path_found else 0
        }
        
        self.results.append(result)
        
        json_data = {
            'best_moves': self.best_moves,
            'best_score': self.best_score,
            'episode': self.episode,
            'results': self.results[-20:]
        }
        
        with open('resultados.json', 'w') as f:
            json.dump(json_data, f)
        
        self.episode += 1
        self.episode_start_time = time.time()

def main():
    print("Acesse http://localhost:8000/monitor_de_resultados.html para ver os resultados")
    print("Pressione ESC para sair")
    
    env = ResourceCollector()
    clock = pygame.time.Clock()
    running = True
       
    while running:
        running = env.handle_events()
        
        if len(env.custom_resources) == 5 and env.can_start and not env.is_paused:
            action = env.choose_action(env.get_state_key())
            _, _, done = env.step(action)
            
            if done and env.auto_continue:
                env.reset()
        
        env.render()
        clock.tick(10)
    pygame.quit()

if __name__ == "__main__":
    main()