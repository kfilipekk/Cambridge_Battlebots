"""Starter bot - a simple example to demonstrate usage of the Controller API."""

import random
import collections
import sys
from cambc import Controller, Direction, EntityType, Environment, Position

CARDINALS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
ALL_DIRS = [d for d in Direction if d != Direction.CENTRE]

##cartography: We build a map from our combined vision
_KNOWLEDGE_MAP = {}

class Player:
    def __init__(self):
        self.state = "INIT"
        self.history = []
        self.heading = None
        self.target_ore = None
        self.spawned_bots = 0
        self.role = "MINER"
        self.turn_offset = random.choice([-1, 1])
        
    def update_cartography(self, c: Controller):
        global _KNOWLEDGE_MAP
        my_team = c.get_team()
        
        ##update buildings in vision
        for bid in c.get_nearby_buildings():
            try:
                b_pos = c.get_position(id=bid)
                b_type = c.get_entity_type(id=bid)
                b_team = c.get_team(id=bid) if hasattr(c, 'get_team') else my_team
                
                ##assign simple icons
                icon = "?"
                if b_type == EntityType.CORE: icon = "C" if b_team == my_team else "c"
                elif b_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR): icon = "v" if b_team == my_team else "x"
                elif b_type == EntityType.ROAD: icon = "="
                elif b_type == EntityType.BRIDGE: icon = "B"
                elif b_type == EntityType.SPLITTER: icon = "S" if b_team == my_team else "s"
                elif b_type in (EntityType.GUNNER, EntityType.SENTINEL, EntityType.BREACH): icon = "T" if b_team == my_team else "t"
                elif b_type == EntityType.FOUNDRY: icon = "F" if b_team == my_team else "f"
                elif b_type == EntityType.HARVESTER: icon = "H" if b_team == my_team else "h"
                elif b_type == EntityType.LAUNCHER: icon = "L" if b_team == my_team else "l"
                
                _KNOWLEDGE_MAP[(b_pos.x, b_pos.y)] = icon
            except Exception:
                pass


    def run(self, c: Controller) -> None:
        self.update_cartography(c)
        etype = c.get_entity_type()

        if etype == EntityType.CORE:
            ##print the final mapped map occasionally
            if c.get_current_round() % 100 == 0 and c.get_current_round() > 50:
                width = c.get_map_width()
                height = c.get_map_height()
                hdr = f"\n@@DYNAMIC_MAP_BEGIN[{c.get_current_round()}]@@\n"
                for y in range(height):
                    row = ""
                    for x in range(width):
                        pos = Position(x, y)
                        val = _KNOWLEDGE_MAP.get((x, y))
                        if val is None:
                            try:
                                if c.is_in_vision(pos):
                                    env = c.get_tile_env(pos)
                                    ore = c.get_tile_ore(pos)
                                    if env == Environment.WALL: val = "#"
                                    elif ore == 1: val = "M" 
                                    elif ore == 2: val = "A" 
                                    else: val = "."
                                    _KNOWLEDGE_MAP[(x, y)] = val
                                else:
                                    val = " " ##fog of war
                            except Exception:
                                val = " "
                        
                        ##just in case val is still None
                        if val is None: val = " "
                        row += val
                    hdr += row + "\n"
                hdr += f"@@DYNAMIC_MAP_END@@]@@\n"
                print(hdr, file=sys.stderr)

            self.run_core(c)
        elif etype == EntityType.BUILDER_BOT:
            self.run_builder(c)

    def run_core(self, c: Controller):
        if c.get_action_cooldown() != 0:
            return
            
        ti, ax = c.get_global_resources()
        
        ##dynamic bot cap based on titanium buffer
        dynamic_bot_cap = min(36, 6 + int(ti / 75))
        
        if self.spawned_bots < dynamic_bot_cap:
            builder_cost = c.get_builder_bot_cost()[0]
            harvester_cost = c.get_harvester_cost()[0]
            conv_cost = c.get_conveyor_cost()[0]
            
            ##keep a healthy buffer so builders can always afford a Harvester + Conveyor chain!
            buffer = harvester_cost + (20 * conv_cost) + 20
            
            if ti > builder_cost + buffer:
                spawn_dirs = list(CARDINALS)
                random.shuffle(spawn_dirs)
                for d in spawn_dirs:
                    target = c.get_position().add(d)
                    if c.can_spawn(target):
                        c.spawn_builder(target)
                        self.spawned_bots += 1
                        break

    def check_and_build_foundry(self, c: Controller):
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        
        ##wait for a massive titanium reserve before building
        ##if we double our costs, we need cash to survive the transition.
        if ti < (120 * scale) + 500: 
            return False
            
        ##we need Raw Axionite flowing into the core first
        if ax < 10:
            return False

        core_pos = self.history[0] if self.history else c.get_position()
        
        ##ensure we only ever build one foundry
        foundry_claimed = False
        for eid in c.get_nearby_entities():
            if c.get_entity_type(eid) == EntityType.MARKER:
                if c.get_marker_value(eid) == 999:
                    foundry_claimed = True
                    break
                    
        for tile in c.get_nearby_tiles(25):
            bid = c.get_tile_building_id(tile)
            if bid and c.get_entity_type(bid) == EntityType.FOUNDRY:
                foundry_claimed = True
                break

        if foundry_claimed:
            return False 
            
        ##claim and build the foundry
        if c.can_place_marker(c.get_position()):
            c.place_marker(c.get_position(), 999)
            
        for d in CARDINALS:
            build_pos = core_pos.add(d)
            if c.is_tile_empty(build_pos):
                if hasattr(c, 'can_build_foundry') and c.can_build_foundry(build_pos):
                    c.build_foundry(build_pos)
                    return True
                    
        return False

    def assign_role(self, c: Controller):
        round_num = c.get_current_round()
        roll = random.random()
        
        ##disabled Saboteur until we fix its ammo routing. Focus entirely on economy!
        if False:
            self.role = "REFINER"
        else:
            self.role = "MINER"

    def run_builder(self, c: Controller):
        if self.state == "INIT":
            self.state = "WANDER"
            self.history.append(c.get_position())
            
            self.assign_role(c)
            
            valid_dirs = []
            for d in CARDINALS:
                np = c.get_position().add(d)
                if c.is_tile_empty(np) and c.get_tile_building_id(np) is None:
                    valid_dirs.append(d)
            self.heading = random.choice(valid_dirs) if valid_dirs else random.choice(CARDINALS)

        if self.role == "SABOTEUR":
            self.do_sabotage(c)
            return

        if self.state == "WANDER":
            ##anyone wandering near the base can help build the foundry
            if len(self.history) <= 3:
                if self.check_and_build_foundry(c):
                    return ##action spent!

            ##if we just arrived back at the core, apply the Scatter Protocol again
            if len(self.history) <= 1:
                valid_dirs = []
                for d in CARDINALS:
                    np = c.get_position().add(d)
                    if c.is_tile_empty(np) and c.get_tile_building_id(np) is None:
                        valid_dirs.append(d)
                if valid_dirs and self.heading not in valid_dirs:
                     self.heading = random.choice(valid_dirs)

            self.do_wander(c)
            
        elif self.state == "RETURN":
            self.do_return(c)
            
    def build_bunker(self, c: Controller, target_pos: Position, facing_dir: Direction):
        """
        Builds a Splitter facing the enemy, and tries to build 3 Turrets around it.
        Upgrades to BREACH turrets if Refined Axionite is available!
        """
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        
        ##check if we have Refined Axionite to afford Breach Turrets
        use_breach = ax >= int(15 * scale)
        
        if use_breach:
            if ti < int(100 * scale): 
                return False 
        else:
            if ti < int(60 * scale): 
                return False

        ##build the Splitter
        if facing_dir not in CARDINALS:
            facing_dir = random.choice(CARDINALS)
            
        if c.can_build_splitter(target_pos, facing_dir):
            c.build_splitter(target_pos, facing_dir)

        idx = CARDINALS.index(facing_dir)
        left_dir = CARDINALS[(idx - 1) % 4]
        right_dir = CARDINALS[(idx + 1) % 4]
        output_dirs = [facing_dir, left_dir, right_dir]
        
        ##slap the best available turrets on the outputs!
        built_any = False
        for d in output_dirs:
            turret_pos = target_pos.add(d)
            if use_breach:
                if c.can_build_breach(turret_pos, facing_dir):
                    c.build_breach(turret_pos, facing_dir)
                    built_any = True
            else:
                if c.can_build_gunner(turret_pos, facing_dir):
                    c.build_gunner(turret_pos, facing_dir)
                    built_any = True
                
        return built_any

    def do_sabotage(self, c: Controller):
        if c.get_action_cooldown() > 0 or c.get_move_cooldown() > 0:
            return
            
        my_pos = c.get_position()
        
        start_pos = self.history[0] if self.history else my_pos
        enemy_x = c.get_map_width() - 1 - start_pos.x
        enemy_y = c.get_map_height() - 1 - start_pos.y
        enemy_core_guess = Position(enemy_x, enemy_y)

        if my_pos.distance_squared(enemy_core_guess) <= 36: 
            attack_dir = my_pos.direction_to(enemy_core_guess)
            if attack_dir:
                build_pos = my_pos.add(attack_dir) 
                if self.build_bunker(c, build_pos, attack_dir):
                    self.state = "RETURN" 
                return
        
        best_d = my_pos.direction_to(enemy_core_guess)
        
        if best_d and not self.try_step(c, best_d):
            self.try_step(c, self.heading)

    def do_wander(self, c: Controller):
        if c.get_action_cooldown() > 0 or c.get_move_cooldown() > 0:
            return

        my_pos = c.get_position()
        
        ##look for unmined ore
        if not self.target_ore:
            best_ore = None
            closest_dist = 99999
            for tile in c.get_nearby_tiles(20):
                env = c.get_tile_env(tile)
                if env in (Environment.ORE_TITANIUM, Environment.ORE_AXIONITE):
                    if c.get_tile_building_id(tile) is None:
                        if self.role == "REFINER":
                            dist_penalty = -99999 if env == Environment.ORE_AXIONITE else 99999
                        else:
                            dist_penalty = -99999 if env == Environment.ORE_TITANIUM else 0
                            
                        has_core = False
                        for cx in range(-1, 2):
                            for cy in range(-1, 2):
                                c_pos = Position(tile.x + cx, tile.y + cy)
                                if c.is_in_vision(c_pos) and (0 <= c_pos.x < c.get_map_width()) and (0 <= c_pos.y < c.get_map_height()):
                                    bid = c.get_tile_building_id(c_pos)
                                    if bid and c.get_entity_type(bid) == EntityType.CORE:
                                        has_core = True
                        if not has_core:
                            dist = my_pos.distance_squared(tile) + dist_penalty
                            if dist < closest_dist:
                                closest_dist = dist
                                best_ore = tile
            if best_ore:
                self.target_ore = best_ore

        if self.target_ore and c.is_in_vision(self.target_ore):
            if c.get_tile_building_id(self.target_ore) is not None:
                self.target_ore = None

        if self.target_ore:
            dist = my_pos.distance_squared(self.target_ore)
            ##must be exactly cardinal distance 1 to ensure conveyor connects
            if dist == 1:
                ##prune history first to get true optimal return path length
                opt_hist = [self.history[0]]
                curr_idx = 0
                while curr_idx < len(self.history) - 1:
                    furthest_adj = curr_idx + 1
                    for j in range(len(self.history)-1, curr_idx, -1):
                        if self.history[curr_idx].distance_squared(self.history[j]) == 1:
                            furthest_adj = j
                            break
                    opt_hist.append(self.history[furthest_adj])
                    curr_idx = furthest_adj
                
                ti, _ = c.get_global_resources()
                harv_cost = c.get_harvester_cost()[0]
                conv_cost = c.get_conveyor_cost()[0]
                
                ##exact Ti needed for Harvester + Conveyors back
                required_ti = harv_cost + (len(opt_hist) * conv_cost) + 10
                
                if ti >= required_ti and c.can_build_harvester(self.target_ore):
                    c.build_harvester(self.target_ore)
                    self.state = "RETURN" 
                    self.target_ore = None
                    self.history = opt_hist
                else:
                    ##if we can't afford it yet, just WAIT and camp the spot!
                    if c.is_in_vision(self.target_ore) and c.get_tile_building_id(self.target_ore) is not None:
                        self.target_ore = None
                        self._turn()
                        self.try_step(c, self.heading)
                return
            else:
                best_d = None
                best_d_dist = 99999
                for d in CARDINALS:
                    np = my_pos.add(d)
                    d_dist = np.distance_squared(self.target_ore)
                    if d_dist < best_d_dist:
                        best_d = d
                        best_d_dist = d_dist
                if best_d:
                    moved = self.try_step(c, best_d)
                    if not moved:
                        self.target_ore = None
                return
                
        self.try_step(c, self.heading)

    def try_step(self, c: Controller, d: Direction):
        my_pos = c.get_position()
        
        ti, _ = c.get_global_resources()
        
        conv_cost = c.get_conveyor_cost()[0]
        harv_cost = c.get_harvester_cost()[0]
        
        ##prevent wandering bots from starving returning bots
        if self.target_ore is not None:
            ##overestimate return cost to prevent starvation of the global pool
            can_afford_road = ti >= harv_cost + (len(self.history) * conv_cost) + 25
        else:
            reserve_needed = harv_cost + (20 * conv_cost) + 20
            can_afford_road = ti >= reserve_needed

        if d is not None and d in CARDINALS:
            self.heading = d
            
        if self.state == "WANDER" and can_afford_road and random.random() < 0.02:
            idx = CARDINALS.index(self.heading)
            self.heading = CARDINALS[(idx + random.choice([-1, 1])) % 4]
            
        idx = CARDINALS.index(self.heading)
        
        check_order = [
            self.heading,
            CARDINALS[(idx + self.turn_offset) % 4],
            CARDINALS[(idx - self.turn_offset) % 4],
            CARDINALS[(idx + 2) % 4]
        ]

        for check_d in check_order:
            np = my_pos.add(check_d)
            if 0 <= np.x < c.get_map_width() and 0 <= np.y < c.get_map_height():
                if c.can_move(check_d):
                    c.move(check_d)
                    self.heading = check_d
                    if np in self.history:
                        cut_idx = self.history.index(np)
                        self.history = self.history[:cut_idx+1]
                    else:
                        self.history.append(my_pos)
                    return True
                    
                elif c.is_tile_empty(np) and c.get_tile_building_id(np) is None:
                    if can_afford_road and c.can_build_road(np):
                        c.build_road(np)
                        self.heading = check_d
                        return True
                        
        self._turn()
        return False

    def _turn(self):
        idx = CARDINALS.index(self.heading)
        self.heading = CARDINALS[(idx + self.turn_offset) % 4]

    def do_return(self, c: Controller):
        if c.get_action_cooldown() > 0 or c.get_move_cooldown() > 0:
            return
            
        my_pos = c.get_position()
        my_building = c.get_tile_building_id(my_pos)
        
        if len(self.history) == 0:
            ##---> CRITICAL FIX: Ensure the final conveyor connects to the Core! <---
            core_d = None
            for d in ALL_DIRS:
                np = my_pos.add(d)
                if c.is_in_vision(np):
                    bid = c.get_tile_building_id(np)
                    if bid is not None and c.get_entity_type(bid) == EntityType.CORE:
                        core_d = d
                        break
                        
            if core_d is not None:
                needs_conveyor = True
                if my_building is not None:
                    b_type = c.get_entity_type(my_building)
                    if b_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE):
                        needs_conveyor = False
                        
                if needs_conveyor:
                    ti, ax = c.get_global_resources()
                    conv_cost = c.get_conveyor_cost()[0]
                    if ti < conv_cost:
                        return 
                        
                    if my_building is not None and c.get_entity_type(my_building) == EntityType.ROAD:
                        if c.can_destroy(my_pos):
                            c.destroy(my_pos)
                            
                    use_armoured = False
                    arm_cost = c.get_armoured_conveyor_cost()
                    built_conveyor = False
                    if ax >= arm_cost[1] and ti >= arm_cost[0]:
                        if hasattr(c, 'can_build_armoured_conveyor') and c.can_build_armoured_conveyor(my_pos, core_d):
                            c.build_armoured_conveyor(my_pos, core_d)
                            use_armoured = True
                            built_conveyor = True
                            
                    if not use_armoured and c.can_build_conveyor(my_pos, core_d):
                        c.build_conveyor(my_pos, core_d)
                        built_conveyor = True
                        
                    if not built_conveyor:
                        return

            self.state = "WANDER"
            self.assign_role(c)
            self.history = [my_pos]
            return
            
        target_pos = self.history[-1]
        
        ##eARLY CORE ARRIVAL FIX
        target_building = None
        if c.is_in_vision(target_pos):
            target_building = c.get_tile_building_id(target_pos)
            
        if target_building is not None and c.get_entity_type(target_building) == EntityType.CORE:
            d = None
            for cd in ALL_DIRS:
                if my_pos.add(cd) == target_pos:
                    d = cd
                    break
                    
            if d is not None:
                needs_conveyor = True
                if my_building is not None:
                    b_type = c.get_entity_type(my_building)
                    if b_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR, EntityType.CORE, EntityType.HARVESTER):
                        needs_conveyor = False
                
                if needs_conveyor:
                    ti, ax = c.get_global_resources()
                    conv_cost = c.get_conveyor_cost()[0]
                    if ti < conv_cost:
                        return 
                        
                    if my_building is not None and c.get_entity_type(my_building) == EntityType.ROAD:
                        if c.can_destroy(my_pos):
                            c.destroy(my_pos)
                            
                    use_armoured = False
                    arm_cost = c.get_armoured_conveyor_cost()
                    built_conveyor = False
                    if ax >= arm_cost[1] and ti >= arm_cost[0]:
                        if hasattr(c, 'can_build_armoured_conveyor') and c.can_build_armoured_conveyor(my_pos, d):
                            c.build_armoured_conveyor(my_pos, d)
                            use_armoured = True
                            built_conveyor = True
                            
                    if not use_armoured and c.can_build_conveyor(my_pos, d):
                        c.build_conveyor(my_pos, d)
                        built_conveyor = True
                        
                    if not built_conveyor:
                        return
            
            self.history = [my_pos]
            self.state = "WANDER"
            self.assign_role(c) 
            return

        ##sTANDARD RETURN LOGIC
        if my_pos == target_pos:
            self.history.pop()
            return

        d = None
        for cd in ALL_DIRS:
            if my_pos.add(cd) == target_pos:
                d = cd
                break
                
        if d is None:
            self.history.pop()
            return

        needs_conveyor = True
        if my_building is not None:
            b_type = c.get_entity_type(my_building)
            if b_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
                needs_conveyor = False
            elif b_type in (EntityType.CORE, EntityType.HARVESTER):
                needs_conveyor = False                
        
        if needs_conveyor:
            ti, ax = c.get_global_resources()
            conv_cost = c.get_conveyor_cost()[0]
            if ti < conv_cost:
                return 
                
            if my_building is not None and c.get_entity_type(my_building) == EntityType.ROAD:
                if c.can_destroy(my_pos):
                    c.destroy(my_pos)
                    
            use_armoured = False
            arm_cost = c.get_armoured_conveyor_cost()
            built_conveyor = False
            if ax >= arm_cost[1] and ti >= arm_cost[0]:
                if hasattr(c, 'can_build_armoured_conveyor') and c.can_build_armoured_conveyor(my_pos, d):
                    c.build_armoured_conveyor(my_pos, d)
                    use_armoured = True
                    built_conveyor = True
                    
            if not use_armoured and c.can_build_conveyor(my_pos, d):
                c.build_conveyor(my_pos, d)
                built_conveyor = True
                
            if not built_conveyor:
                ##failed to construct the conveyor (tile blocked, out of Ti, etc). DO NOT LEAVE A GAP!
                return

        ##if a Wandering bot is in our way, just wait.
        if c.can_move(d):
            c.move(d)
            self.history.pop()
        else:
            np = my_pos.add(d)
            if c.is_tile_empty(np) and c.get_tile_building_id(np) is None:
                ti, _ = c.get_global_resources()
                if ti >= 16 and c.can_build_road(np):
                    c.build_road(np)