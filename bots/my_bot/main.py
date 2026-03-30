import collections
import sys
from cambc import Controller, Direction, EntityType, Environment, Position

ALL_DIRS = [Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
            Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST, Direction.NORTHWEST]

class Player:
    def __init__(self):
        self.initialized = False
        self.enemy_core_pos = None
        self.my_core_pos = None
        self.map_w = 0
        self.map_h = 0
        self.is_core = False

    def run(self, c: Controller) -> None:
        if not self.initialized:
            self.map_w = c.get_map_width()
            self.map_h = c.get_map_height()
            self.is_core = (c.get_entity_type() == EntityType.CORE)
            my_pos = c.get_position()
            self.my_core_pos = my_pos
            if not self.is_core:
                for eid in c.get_nearby_buildings(20):
                    if c.get_entity_type(eid) == EntityType.CORE and c.get_team(eid) == c.get_team():
                        self.my_core_pos = c.get_position(eid)
                        break

                        
            self.enemy_core_pos = Position(self.map_w - 1 - self.my_core_pos.x, 
                                           self.map_h - 1 - self.my_core_pos.y)
            self.initialized = True

        etype = c.get_entity_type()
        if etype == EntityType.CORE:
            self.run_core(c)
        elif etype == EntityType.BUILDER_BOT:
            self.run_builder(c)
        elif etype == EntityType.LAUNCHER:
            self.run_launcher(c)

    def run_core(self, c: Controller):
        if c.get_action_cooldown() != 0:
            return
            
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        bot_cost = int(10 * scale)
        buffer = int(100 * scale)
        
        if c.get_current_round() % 50 == 0:
            print(f"CORE round {c.get_current_round()} Ti: {ti} Scale: {scale} BotCost: {bot_cost}", file=sys.stderr)
        
        if ti >= bot_cost + buffer:
            best_dir = self.my_core_pos.direction_to(self.enemy_core_pos)
            spawn_pos = self.my_core_pos.add(best_dir)
            if c.can_spawn(spawn_pos):
                c.spawn_builder(spawn_pos)
            else:
                for d in ALL_DIRS:
                    sp = self.my_core_pos.add(d)
                    if c.can_spawn(sp):
                        c.spawn_builder(sp)
                        break

    def run_builder(self, c: Controller):
        my_pos = c.get_position()
        if c.get_current_round() % 10 == 0:
            print(f"[{c.get_current_round()}] BOT {c.get_id()} at {my_pos} (dist: {my_pos.distance_squared(self.enemy_core_pos)}) "
                  f"AC: {c.get_action_cooldown()} MC: {c.get_move_cooldown()}", file=sys.stderr)
        
        
        if my_pos.distance_squared(self.enemy_core_pos) <= 2:
            print(f"BOT at {my_pos} KAMI on enemy core! dist: {my_pos.distance_squared(self.enemy_core_pos)}", file=sys.stderr)
            if c.get_action_cooldown() == 0:
                c.self_destruct()
            return

        bid = c.get_tile_building_id(my_pos)
        if bid and c.get_team(bid) != c.get_team():
            print(f"BOT at {my_pos} KAMI on enemy building!", file=sys.stderr)
            if c.get_action_cooldown() == 0:
                c.self_destruct()
            return
            
        dist_to_enemy = my_pos.distance_squared(self.enemy_core_pos)
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        
        if dist_to_enemy <= 40:
            has_launcher = False
            for eid in c.get_nearby_buildings(20):
                if c.get_entity_type(eid) == EntityType.LAUNCHER:
                    has_launcher = True
                    break
            
            if not has_launcher and ti >= int(20 * scale) and c.get_action_cooldown() == 0:
                best_lp = None
                best_ld = 9999
                for d in ALL_DIRS:
                    np = my_pos.add(d)
                    ndist = np.distance_squared(self.enemy_core_pos)
                    is_emp = c.is_tile_empty(np)
                    can_b = c.can_build_launcher(np)
                    if c.get_current_round() % 10 == 0:
                        print(f"[{c.get_current_round()}] BOT {c.get_id()} checking {np} for launcher. ndist={ndist} emp={is_emp} can={can_b}", file=sys.stderr)
                    if ndist <= 26 and ndist < best_ld and is_emp and can_b:
                        best_ld = ndist
                        best_lp = np
                if best_lp:
                    print(f"BOT BUILDING LAUNCHER at {best_lp}", file=sys.stderr)
                    c.build_launcher(best_lp)
                    return

        if c.get_move_cooldown() != 0 and c.get_action_cooldown() != 0:
            return

        target_dir = my_pos.direction_to(self.enemy_core_pos)
        next_pos = my_pos.add(target_dir)
        
        passable = True
        if c.is_in_vision(next_pos):
            env = c.get_tile_env(next_pos)
            if env in (Environment.WALL, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                passable = False
            bid_next = c.get_tile_building_id(next_pos)
            if bid_next:
                btype = c.get_entity_type(bid_next)
                if btype not in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE, EntityType.LAUNCHER):
                    passable = False
        
        if not passable:
            next_pos = self.get_next_path_step(c, my_pos, self.enemy_core_pos)
            if not next_pos:
                if c.get_move_cooldown() == 0:
                    for d in ALL_DIRS:
                        if c.can_move(d):
                            c.move(d)
                            break
                return
            target_dir = my_pos.direction_to(next_pos)
            
        if c.get_current_round() % 10 == 0:
            print(f"[{c.get_current_round()}] BOT {c.get_id()} targeting {next_pos}. Empty? {c.is_tile_empty(next_pos)} "
                  f"Env: {c.get_tile_env(next_pos) if c.is_in_vision(next_pos) else 'FOG'} "
                  f"Bid: {c.get_tile_building_id(next_pos) if c.is_in_vision(next_pos) else 'FOG'}", file=sys.stderr)
        built = False
        if c.get_action_cooldown() == 0 and c.is_tile_empty(next_pos):
            conv_cost = int(3 * scale)
            if ti >= conv_cost and c.can_build_conveyor(next_pos, target_dir):
                c.build_conveyor(next_pos, target_dir)
                built = True
            elif ti >= int(1 * scale) and c.can_build_road(next_pos):
                c.build_road(next_pos)
                built = True

        if c.get_move_cooldown() == 0:
            if c.can_move(target_dir):
                c.move(target_dir)
            elif not built:
                idx = ALL_DIRS.index(target_dir)
                for offset in [-1, 1, -2, 2]:
                    sd = ALL_DIRS[(idx + offset) % 8]
                    if c.can_move(sd):
                        c.move(sd)
                        break

    def get_next_path_step(self, c: Controller, start: Position, goal: Position):
        queue = collections.deque([start])
        came_from = {start: None}
        iters = 0
        best_end = start
        min_dist = start.distance_squared(goal)

        while queue and iters < 2500:
            curr = queue.popleft()
            iters += 1
            dist = curr.distance_squared(goal)
            if dist < min_dist:
                min_dist = dist
                best_end = curr
                if min_dist < start.distance_squared(goal) - 10:
                    break

            for d in ALL_DIRS:
                np = curr.add(d)
                if 0 <= np.x < self.map_w and 0 <= np.y < self.map_h:
                    if np not in came_from:
                        passable = True
                        if c.is_in_vision(np):
                            env = c.get_tile_env(np)
                            if env in (Environment.WALL, Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                                passable = False
                            bid = c.get_tile_building_id(np)
                            if bid:
                                btype = c.get_entity_type(bid)
                                if btype not in (EntityType.ROAD, EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE, EntityType.LAUNCHER):
                                    passable = False
                        if passable:
                            came_from[np] = curr
                            queue.append(np)
        
        curr = best_end
        while came_from.get(curr) != start and came_from.get(curr) is not None:
            curr = came_from[curr]
            
        return curr if curr != start else None

    def run_launcher(self, c: Controller):
        if c.get_action_cooldown() != 0:
            return
            
        all_targets = []
        for cx in range(-3, 4):
            for cy in range(-3, 4):
                tp = Position(self.enemy_core_pos.x + cx, self.enemy_core_pos.y + cy)
                all_targets.append(tp)
        all_targets.sort(key=lambda p: p.distance_squared(self.enemy_core_pos))
        
        my_pos = c.get_position()
        bot_to_launch = None
        
        for d in ALL_DIRS:
            adj = my_pos.add(d)
            bot_id = c.get_tile_builder_bot_id(adj)
            if bot_id and c.get_team(bot_id) == c.get_team():
                bot_to_launch = adj
                break
                
        if bot_to_launch:
            for tp in all_targets:
                if c.can_launch(bot_to_launch, tp):
                    c.launch(bot_to_launch, tp)
                    print(f"LAUNCHER at {my_pos} LAUNCHED bot to {tp}", file=sys.stderr)
                    return
