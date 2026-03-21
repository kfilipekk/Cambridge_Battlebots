import random
import heapq

from cambc import Controller, Direction, EntityType, Environment, Position

ALL_DIRS = [
    Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
    Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST, Direction.NORTHWEST
]

def get_walk_path(start_pos, target_pos, c, player):
    w, h = player.width, player.height
    queue = [(max(abs(start_pos.x - target_pos.x), abs(start_pos.y - target_pos.y)), 0, start_pos.x, start_pos.y)]
    costs = {(start_pos.x, start_pos.y): 0}
    came_from = {}
    
    iters = 0
    final_pos = None
    
    while queue and iters < 2000:
        iters += 1
        if iters % 50 == 0 and c.get_cpu_time_elapsed() > 1700:
            break
            
        _, cost, cx, cy = heapq.heappop(queue)
        curr = Position(cx, cy)
        
        if curr == target_pos:
            final_pos = curr
            break
            
        if cost > costs.get((cx, cy), float('inf')):
            continue
            
        for d in ALL_DIRS:
            nx, ny = cx + d.delta()[0], cy + d.delta()[1]
            if not (0 <= nx < w and 0 <= ny < h):
                continue
                
            n_env = player.env_map.get((nx, ny), Environment.EMPTY)
            n_bldg = player.bldg_map.get((nx, ny))
            n_team = player.team_map.get((nx, ny))
            
            if Position(nx, ny) == target_pos:
                ncost = cost + 1
                if ncost < costs.get((nx, ny), float('inf')):
                    costs[(nx, ny)] = ncost
                    heapq.heappush(queue, (ncost + max(abs(nx - target_pos.x), abs(ny - target_pos.y)), ncost, nx, ny))
                    came_from[(nx, ny)] = curr
                continue
                
            if n_env in (Environment.WALL, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                continue
                
            if n_bldg is not None and n_team != c.get_team():
                if n_bldg not in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
                    continue
                
            if (nx, ny) not in player.env_map:
                weight = 10
            elif n_bldg in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE):
                weight = 1
            else:
                weight = 5
                
            ncost = cost + weight
            if ncost < costs.get((nx, ny), float('inf')):
                costs[(nx, ny)] = ncost
                heapq.heappush(queue, (ncost + max(abs(nx - target_pos.x), abs(ny - target_pos.y)), ncost, nx, ny))
                came_from[(nx, ny)] = curr
                
    if not final_pos: return None
    path = []
    curr = final_pos
    while curr != start_pos:
        path.append(curr)
        curr = came_from[(curr.x, curr.y)]
    path.append(start_pos)
    path.reverse()
    return path

def get_conveyor_path(start_pos, target_pos, c, player):
    w, h = player.width, player.height
    queue = [(max(abs(start_pos.x - target_pos.x), abs(start_pos.y - target_pos.y)), 0, start_pos.x, start_pos.y)]
    costs = {(start_pos.x, start_pos.y): 0}
    came_from = {}
    
    iters = 0
    final_pos = None
    
    while queue and iters < 2000:
        iters += 1
        if iters % 50 == 0 and c.get_cpu_time_elapsed() > 1700:
            break
            
        _, cost, cx, cy = heapq.heappop(queue)
        curr = Position(cx, cy)
        
        if curr == target_pos:
            final_pos = curr
            break
            
        if cost > costs.get((cx, cy), float('inf')):
            continue
            
        bldg = player.bldg_map.get((cx, cy))
        team = player.team_map.get((cx, cy))
        
        if bldg in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR) and team == c.get_team():
            d = player.dir_map.get((cx, cy))
            if d:
                nx, ny = cx + d.delta()[0], cy + d.delta()[1]
                if 0 <= nx < w and 0 <= ny < h:
                    ncost = cost + 1
                    if ncost < costs.get((nx, ny), float('inf')):
                        costs[(nx, ny)] = ncost
                        heapq.heappush(queue, (ncost + max(abs(nx - target_pos.x), abs(ny - target_pos.y)), ncost, nx, ny))
                        came_from[(nx, ny)] = curr
            continue
            
        for d in ALL_DIRS:
            nx, ny = cx + d.delta()[0], cy + d.delta()[1]
            if not (0 <= nx < w and 0 <= ny < h):
                continue
                
            n_env = player.env_map.get((nx, ny), Environment.EMPTY)
            n_bldg = player.bldg_map.get((nx, ny))
            n_team = player.team_map.get((nx, ny))
            
            if Position(nx, ny) == target_pos:
                ncost = cost + 1
                if ncost < costs.get((nx, ny), float('inf')):
                    costs[(nx, ny)] = ncost
                    heapq.heappush(queue, (ncost + max(abs(nx - target_pos.x), abs(ny - target_pos.y)), ncost, nx, ny))
                    came_from[(nx, ny)] = curr
                continue
                
            if n_env in (Environment.WALL, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                continue
                
            if n_bldg is not None:
                if n_team != c.get_team():
                    continue
                else:
                    if n_bldg not in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE, EntityType.FOUNDRY):
                        continue
                    
            if (nx, ny) not in player.env_map:
                weight = 40
            elif n_bldg == EntityType.ROAD: weight = 5
            elif n_bldg in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR): weight = 1
            else: weight = 15
            
            ncost = cost + weight
            if ncost < costs.get((nx, ny), float('inf')):
                costs[(nx, ny)] = ncost
                heapq.heappush(queue, (ncost + max(abs(nx - target_pos.x), abs(ny - target_pos.y)), ncost, nx, ny))
                came_from[(nx, ny)] = curr
                
    if not final_pos: return None
    path = []
    curr = final_pos
    while curr != start_pos:
        path.append(curr)
        curr = came_from[(curr.x, curr.y)]
    path.append(start_pos)
    path.reverse()
    return path

class Player:
    def __init__(self):
        self.state = "INIT"
        self.role = "NORMAL"
        self.width = None
        self.height = None
        
        self.env_map = {}
        self.bldg_map = {}
        self.team_map = {}
        self.dir_map = {}
        
        self.core_pos = None
        self.foundry_pos = None
        self.spawned_bots = 0
        
        self.walk_path = []
        self.path = []
        self.path_idx = 0
        self.target = None
        self.target_env = None
        self.stuck_counter = 0

    def update_cartography(self, c: Controller):
        for tile in c.get_nearby_tiles(c.get_vision_radius_sq()):
            tx, ty = tile.x, tile.y
            self.env_map[(tx, ty)] = c.get_tile_env(tile)
            
            bid = c.get_tile_building_id(tile)
            if bid is not None:
                self.bldg_map[(tx, ty)] = c.get_entity_type(bid)
                self.team_map[(tx, ty)] = c.get_team(bid)
                if self.bldg_map[(tx, ty)] in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
                    self.dir_map[(tx, ty)] = c.get_direction(bid)
                else:
                    self.dir_map[(tx, ty)] = None
            else:
                self.bldg_map[(tx, ty)] = None
                self.team_map[(tx, ty)] = None
                self.dir_map[(tx, ty)] = None
                
        for bid in c.get_nearby_buildings():
            b_type = c.get_entity_type(bid)
            b_team = c.get_team(bid)
            if b_type == EntityType.CORE:
                b_pos = c.get_position(bid)
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = b_pos.x + dx, b_pos.y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            self.bldg_map[(nx, ny)] = EntityType.CORE
                            self.team_map[(nx, ny)] = b_team

    def run(self, c: Controller) -> None:
        if self.width is None:
            self.width = c.get_map_width()
            self.height = c.get_map_height()

        self.update_cartography(c)
        etype = c.get_entity_type()

        if etype == EntityType.CORE:
            self.run_core(c)
        elif etype == EntityType.BUILDER_BOT:
            self.run_builder(c)

    def run_core(self, c: Controller):
        if c.get_action_cooldown() != 0:
            return
            
        ti, _ = c.get_global_resources()
        
        ##swarm limits gently increment into late game to limit Scale inflation
        bot_cap = min(18, 5 + c.get_current_round() // 120)
        
        if self.spawned_bots < bot_cap:
            cost_ti, _ = c.get_builder_bot_cost()
            required_ti = cost_ti + 80 + (self.spawned_bots * 30)
            
            if ti >= required_ti:
                spawn_dirs = list(ALL_DIRS)
                random.shuffle(spawn_dirs)
                for d in spawn_dirs:
                    target = c.get_position().add(d)
                    if c.can_spawn(target):
                        c.spawn_builder(target)
                        self.spawned_bots += 1
                        
                        ##bot ##8 receives the Foundry marker command
                        if c.can_place_marker(target):
                            c.place_marker(target, 999 if self.spawned_bots == 8 else 1)
                        break

    def run_builder(self, c: Controller):
        if self.state == "INIT":
            self.core_pos = c.get_position()
            for bid in c.get_nearby_buildings():
                if c.get_entity_type(bid) == EntityType.CORE and c.get_team(bid) == c.get_team():
                    self.core_pos = c.get_position(bid)
                    break
                    
            my_pos = c.get_position()
            my_bid = c.get_tile_building_id(my_pos)
            self.role = "NORMAL"
            
            ##read spawn directive
            if my_bid and c.get_entity_type(my_bid) == EntityType.MARKER:
                if c.get_marker_value(my_bid) == 999:
                    self.role = "FOUNDRY"
                    self.state = "BUILD_FOUNDRY"
                else:
                    self.state = "WANDER"
            else:
                self.state = "WANDER"
                
            self.stuck_counter = 0

        if self.role == "FOUNDRY":
            self.run_foundry_bot(c)
        else:
            if self.state == "WANDER":
                self.do_wander(c)
            elif self.state == "RETURN":
                self.do_return(c)

    def run_foundry_bot(self, c: Controller):
        if self.state == "BUILD_FOUNDRY":
            if not self.foundry_pos:
                cx, cy = self.core_pos.x, self.core_pos.y
                best_fp = None
                
                ##scan precisely distances capable of feeding the core automatically (Chebyshev Distance = 2 Edge Tile)
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if abs(dx) == 2 or abs(dy) == 2:
                            pos = Position(cx + dx, cy + dy)
                            if 0 <= pos.x < self.width and 0 <= pos.y < self.height:
                                if self.env_map.get((pos.x, pos.y), Environment.EMPTY) == Environment.EMPTY:
                                    if self.bldg_map.get((pos.x, pos.y)) is None:
                                        best_fp = pos
                                        break
                    if best_fp: break
                
                if best_fp:
                    self.foundry_pos = best_fp
                else:
                    self.role = "NORMAL"
                    self.state = "WANDER"
                    return
                    
            my_pos = c.get_position()
            if my_pos.distance_squared(self.foundry_pos) <= 2:
                if c.get_action_cooldown() == 0:
                    ti, ax = c.get_global_resources()
                    f_cost, _ = c.get_foundry_cost()
                    if ti >= f_cost:
                        if c.can_build_foundry(self.foundry_pos):
                            c.build_foundry(self.foundry_pos)
                            self.bldg_map[(self.foundry_pos.x, self.foundry_pos.y)] = EntityType.FOUNDRY
                            self.state = "FIND_TI"
                            self.target_env = Environment.ORE_TITANIUM
                            self.walk_path = []
            else:
                self.target = self.foundry_pos
                self._step_walk_path(c)

        elif self.state == "FIND_TI":
            self._find_ore_and_build(c, Environment.ORE_TITANIUM, "ROUTE_TI")

        elif self.state == "ROUTE_TI":
            if self._route_to_target(c, self.foundry_pos):
                self.state = "FIND_AX"
                self.target_env = Environment.ORE_AXIONITE
                self.walk_path = []

        elif self.state == "FIND_AX":
            self._find_ore_and_build(c, Environment.ORE_AXIONITE, "ROUTE_AX")

        elif self.state == "ROUTE_AX":
            if self._route_to_target(c, self.foundry_pos):
                self.state = "DONE"
                
        elif self.state == "DONE":
            self.role = "NORMAL"
            self.state = "WANDER"

    def do_wander(self, c: Controller):
        my_pos = c.get_position()
        
        if c.get_action_cooldown() == 0:
            for d in ALL_DIRS:
                adj = my_pos.add(d)
                if c.is_in_vision(adj):
                    env = self.env_map.get((adj.x, adj.y))
                    if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                        bldg = self.bldg_map.get((adj.x, adj.y))
                        if bldg is None or bldg == EntityType.MARKER:
                            ti, _ = c.get_global_resources()
                            h_cost, _ = c.get_harvester_cost()
                            if ti >= h_cost:
                                if bldg == EntityType.MARKER and c.can_destroy(adj):
                                    c.destroy(adj)
                                if c.can_build_harvester(adj):
                                    c.build_harvester(adj)
                                    self.bldg_map[(adj.x, adj.y)] = EntityType.HARVESTER
                                    self.team_map[(adj.x, adj.y)] = c.get_team()
                                    self.state = "RETURN"
                                    self.path = get_conveyor_path(my_pos, self.core_pos, c, self)
                                    self.path_idx = 0
                                    self.stuck_counter = 0
                                    return
                                    
        if not self.walk_path or self.path_idx >= len(self.walk_path) - 1:
            self.target = self.find_new_ore_target(c, self)
            self.walk_path = get_walk_path(my_pos, self.target, c, self)
            self.path_idx = 0
            if not self.walk_path: return
                
        self._step_walk_path(c)

    def do_return(self, c: Controller):
        if self._route_to_target(c, self.core_pos):
            self.state = "WANDER"
            self.target = None
            self.path = []

    def _find_ore_and_build(self, c, ore_type, next_state):
        my_pos = c.get_position()
        
        if c.get_action_cooldown() == 0:
            for d in ALL_DIRS:
                adj = my_pos.add(d)
                if c.is_in_vision(adj):
                    env = self.env_map.get((adj.x, adj.y))
                    if env == ore_type:
                        bldg = self.bldg_map.get((adj.x, adj.y))
                        if bldg is None or bldg == EntityType.MARKER:
                            ti, _ = c.get_global_resources()
                            h_cost, _ = c.get_harvester_cost()
                            if ti >= h_cost:
                                if bldg == EntityType.MARKER and c.can_destroy(adj):
                                    c.destroy(adj)
                                if c.can_build_harvester(adj):
                                    c.build_harvester(adj)
                                    self.bldg_map[(adj.x, adj.y)] = EntityType.HARVESTER
                                    self.team_map[(adj.x, adj.y)] = c.get_team()
                                    self.state = next_state
                                    self.path = get_conveyor_path(my_pos, self.foundry_pos, c, self)
                                    self.path_idx = 0
                                    self.stuck_counter = 0
                                    return
                                    
        if not self.walk_path or self.path_idx >= len(self.walk_path) - 1 or getattr(self, 'target_env', None) != ore_type:
            best_dist = float('inf')
            best_ore = None
            for (x, y), env in self.env_map.items():
                if env == ore_type:
                    pos = Position(x, y)
                    if self.bldg_map.get((x, y)) == EntityType.HARVESTER:
                        continue
                    dist = my_pos.distance_squared(pos)
                    if dist < best_dist:
                        best_dist = dist
                        best_ore = pos
                        
            if best_ore:
                self.target = best_ore
                self.target_env = ore_type
                self.walk_path = get_walk_path(my_pos, self.target, c, self)
                self.path_idx = 0
            else:
                self.target = self._get_explore_target(c)
                self.walk_path = get_walk_path(my_pos, self.target, c, self)
                self.path_idx = 0
                
        self._step_walk_path(c)

    def _route_to_target(self, c, target_pos):
        my_pos = c.get_position()
        
        if not self.path or self.path_idx >= len(self.path) - 1:
            return True
            
        curr_pos = self.path[self.path_idx]
        if my_pos != curr_pos:
            self.path = get_conveyor_path(my_pos, target_pos, c, self)
            self.path_idx = 0
            if not self.path:
                return True
            return False
            
        next_pos = self.path[self.path_idx + 1]
        expected_dir = my_pos.direction_to(next_pos)
        
        my_bid = c.get_tile_building_id(my_pos)
        my_bldg = c.get_entity_type(my_bid) if my_bid else None
        
        if my_bldg not in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
            if c.get_action_cooldown() == 0:
                ti, _ = c.get_global_resources()
                cost, _ = c.get_conveyor_cost()
                if ti >= cost:
                    if my_bldg == EntityType.ROAD and c.can_destroy(my_pos):
                        c.destroy(my_pos)
                    if c.can_build_conveyor(my_pos, expected_dir):
                        c.build_conveyor(my_pos, expected_dir)
                        self.bldg_map[(my_pos.x, my_pos.y)] = EntityType.CONVEYOR
                        self.team_map[(my_pos.x, my_pos.y)] = c.get_team()
                        self.dir_map[(my_pos.x, my_pos.y)] = expected_dir
                    else:
                        self.stuck_counter += 1
                        if self.stuck_counter > 10:
                            self._dodge_and_repath_conveyor(c, target_pos)
            return False
            
        elif c.get_direction(my_bid) != expected_dir:
            if c.get_team(my_bid) == c.get_team():
                self.path = get_conveyor_path(my_pos, target_pos, c, self)
                self.path_idx = 0
            return False
            
        next_bid = c.get_tile_building_id(next_pos)
        next_bldg = c.get_entity_type(next_bid) if next_bid else None
        next_team = c.get_team(next_bid) if next_bid else None
        
        passable = False
        if next_team == c.get_team():
            if next_bldg in (EntityType.CORE, EntityType.FOUNDRY):
                passable = True
            elif next_bldg in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
                passable = True

        if not passable:
            if next_bldg not in (None, EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR) and next_team == c.get_team():
                self.path = get_conveyor_path(my_pos, target_pos, c, self)
                self.path_idx = 0
                return False

            if c.get_action_cooldown() == 0:
                ti, _ = c.get_global_resources()
                cost, _ = c.get_conveyor_cost()
                if ti >= cost:
                    if self.path_idx + 2 < len(self.path):
                        next_dir = next_pos.direction_to(self.path[self.path_idx + 2])
                    else:
                        next_dir = Direction.NORTH
                        
                    if next_bldg is not None and next_team == c.get_team() and c.can_destroy(next_pos):
                        c.destroy(next_pos)
                    if c.can_build_conveyor(next_pos, next_dir):
                        c.build_conveyor(next_pos, next_dir)
                        self.bldg_map[(next_pos.x, next_pos.y)] = EntityType.CONVEYOR
                        self.team_map[(next_pos.x, next_pos.y)] = c.get_team()
                        self.dir_map[(next_pos.x, next_pos.y)] = next_dir
                    else:
                        self.stuck_counter += 1
                        if self.stuck_counter > 10:
                            self._dodge_and_repath_conveyor(c, target_pos)
            return False

        if c.get_move_cooldown() == 0:
            if c.can_move(expected_dir):
                c.move(expected_dir)
                self.path_idx += 1
                self.stuck_counter = 0
            else:
                self.stuck_counter += 1
                if self.stuck_counter > 10:
                    self._dodge_and_repath_conveyor(c, target_pos)
                    
        return False

    def _step_walk_path(self, c: Controller):
        my_pos = c.get_position()
        if not self.walk_path or self.path_idx >= len(self.walk_path) - 1:
            return True
            
        curr_pos = self.walk_path[self.path_idx]
        if my_pos != curr_pos:
            self.walk_path = get_walk_path(my_pos, self.target, c, self)
            self.path_idx = 0
            if not self.walk_path: return True
            
        next_pos = self.walk_path[self.path_idx + 1]
        
        if c.is_in_vision(next_pos):
            n_env = c.get_tile_env(next_pos)
            n_bid = c.get_tile_building_id(next_pos)
            n_bldg = c.get_entity_type(n_bid) if n_bid else None
            n_team = c.get_team(n_bid) if n_bid else None
            
            is_enemy_road = n_bldg in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR) and n_team != c.get_team()
            if n_env == Environment.WALL or (n_bldg and n_team != c.get_team() and not is_enemy_road):
                self.walk_path = []
                return False
                
            if n_bldg is None and n_env == Environment.EMPTY and c.get_action_cooldown() == 0:
                ti, _ = c.get_global_resources()
                cost, _ = c.get_road_cost()
                if ti >= cost and c.can_build_road(next_pos):
                    c.build_road(next_pos)
                    
        if c.get_move_cooldown() == 0 and c.is_tile_passable(next_pos):
            d = my_pos.direction_to(next_pos)
            if c.can_move(d):
                c.move(d)
                self.path_idx += 1
                self.stuck_counter = 0
            else:
                self.stuck_counter += 1
                if self.stuck_counter > 5:
                    self._dodge(c)
        elif not c.is_tile_passable(next_pos):
            self.stuck_counter += 1
            if self.stuck_counter > 5:
                self._dodge(c)
        return False

    def _dodge(self, c: Controller):
        for dodge_dir in ALL_DIRS:
            if c.can_move(dodge_dir):
                c.move(dodge_dir)
                break
        self.walk_path = []
        self.stuck_counter = 0
        
    def _dodge_and_repath_conveyor(self, c: Controller, target_pos):
        for dodge_dir in ALL_DIRS:
            if c.can_move(dodge_dir):
                c.move(dodge_dir)
                break
        self.path = get_conveyor_path(c.get_position(), target_pos, c, self)
        self.path_idx = 0
        self.stuck_counter = 0

    def find_new_ore_target(self, c: Controller, player):
        my_pos = c.get_position()
        best_dist = float('inf')
        best_ore = None
        
        my_quadrant = c.get_id() % 4
        cx, cy = self.core_pos.x, self.core_pos.y
        wants_axionite = (c.get_id() % 4 == 0)
        
        ore_types = [Environment.ORE_TITANIUM, Environment.ORE_AXIONITE]
        if wants_axionite:
            ore_types = [Environment.ORE_AXIONITE, Environment.ORE_TITANIUM]
            
        for primary_ore in ore_types:
            for (x, y), env in player.env_map.items():
                if env == primary_ore:
                    pos = Position(x, y)
                    if player.bldg_map.get((x, y)) == EntityType.HARVESTER:
                        continue
                    
                    dist = my_pos.distance_squared(pos)
                    
                    is_right = x > cx
                    is_bottom = y > cy
                    ore_quadrant = (1 if is_right else 0) + (2 if is_bottom else 0)
                    if my_quadrant != ore_quadrant:
                        dist += 150
                        
                    noise = (pos.x * 73 + pos.y * 31 + c.get_id() * 11) % 50
                    dist += noise
                    
                    if dist < best_dist:
                        best_dist = dist
                        best_ore = pos
            if best_ore:
                return best_ore
                
        return self._get_explore_target(c)

    def _get_explore_target(self, c):
        unknowns = []
        for x in range(0, self.width, 3):
            for y in range(0, self.height, 3):
                if (x, y) not in self.env_map:
                    unknowns.append(Position(x, y))
        if unknowns:
            return random.choice(unknowns)
        return Position(random.randint(0, self.width-1), random.randint(0, self.height-1))