"""Starter bot - a simple example to demonstrate usage of the Controller API."""

import random
import collections
from cambc import Controller, Direction, EntityType, Environment, Position

CARDINALS = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
ALL_DIRS = [d for d in Direction if d != Direction.CENTRE]


class Player:
    def __init__(self):
        self.state = "INIT"
        self.history = []
        self.heading = None
        self.target_ore = None
        self.spawned_bots = 0
        self.role = "MINER"
        
    def run(self, c: Controller) -> None:
        etype = c.get_entity_type()
        if etype == EntityType.CORE:
            self.run_core(c)
        elif etype == EntityType.BUILDER_BOT:
            self.run_builder(c)

    def run_core(self, c: Controller):
        if c.get_action_cooldown() != 0:
            return
            
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        
        ##tHE FIX: Hard cap at 15 bots to prevent hyper-inflation and core gridlock!
        dynamic_bot_cap = min(15, 5 + int(ti / 400))
        
        if self.spawned_bots < dynamic_bot_cap:
            builder_cost = int(10 * scale)
            harvester_cost = int(80 * scale)
            
            ##keep a smaller buffer early on so we don't stall early expansion
            buffer = 30 * scale if ti < 500 else 100 * scale 
            
            if ti > builder_cost + harvester_cost + buffer:
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
        if ti < (120 * scale) + 1000: 
            return False
            
        ##we need Raw Axionite flowing into the core first
        if ax < 10:
            return False

        core_pos = self.history[0] if self.history else c.get_position()
        
        ##ensure we only ever build one foundry
        foundry_claimed = False
        for eid in c.get_nearby_entities():
            if c.get_entity_type(eid) == getattr(EntityType, 'MARKER', None):
                if c.get_marker_value(eid) == 999:
                    foundry_claimed = True
                    break
                    
        for tile in c.get_nearby_tiles(25):
            bid = c.get_tile_building_id(tile)
            if bid and c.get_entity_type(bid) == getattr(EntityType, 'AXIONITE_FOUNDRY', None):
                foundry_claimed = True
                break

        if foundry_claimed:
            return False 
            
        ##claim and build the foundry
        if c.can_place_marker(core_pos):
            c.place_marker(core_pos, 999)
            
        for d in CARDINALS:
            build_pos = core_pos.add(d)
            if c.is_tile_empty(build_pos):
                if hasattr(c, 'can_build_axionite_foundry') and c.can_build_axionite_foundry(build_pos):
                    c.build_axionite_foundry(build_pos)
                    return True
                    
        return False

    def run_builder(self, c: Controller):
        if self.state == "INIT":
            self.state = "WANDER"
            self.history.append(c.get_position())
            
            ##tHE NEW ROSTER:
            round_num = c.get_current_round()
            roll = random.random()
            
            if round_num > 700 and roll < 0.25:
                self.role = "SABOTEUR"
            elif round_num > 250 and roll < 0.40: ##15% chance to be a Refiner after early game
                self.role = "REFINER"
            else:
                self.role = "MINER"
            
            valid_dirs = []
            for d in CARDINALS:
                np = c.get_position().add(d)
                if c.is_tile_passable(np) and c.get_tile_building_id(np) is None:
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
                    if c.is_tile_passable(np) and c.get_tile_building_id(np) is None:
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
        ##breach costs 30 Ti + 10 Ax. For 3 turrets, we want a healthy buffer.
        use_breach = ax >= int(15 * scale)
        
        if use_breach:
            if ti < int(100 * scale): 
                return False ##wait for Titanium to catch up
        else:
            if ti < int(60 * scale): 
                return False

        ##build the Splitter
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
        
        ##tHE SYMMETRY TRICK: Calculate enemy core location mathematically
        ##use our spawn location (first item in history) to find our side's core
        start_pos = self.history[0] if self.history else my_pos
        enemy_x = c.get_map_width() - 1 - start_pos.x
        enemy_y = c.get_map_height() - 1 - start_pos.y
        enemy_core_guess = Position(enemy_x, enemy_y)

        ##dROP TURRETS: If we are in the hot zone (within 15 tiles)
        if my_pos.distance_squared(enemy_core_guess) < 225: 
            ##get the direction pointing AT the enemy core
            attack_dir = my_pos.direction_to(enemy_core_guess)
            
            if attack_dir:
                ##step forward once so we have room to build behind us
                build_pos = my_pos.add(attack_dir) 
                
                if self.build_bunker(c, build_pos, attack_dir):
                    ##now that the bunker is placed, step backward and start laying
                    ##a standard conveyor belt to bring ammo to the Splitter!
                    self.history = [self.history[0], my_pos] 
                    self.state = "RETURN" 
                return
        
        ##rELENTLESS MARCH
        ##use the built-in compass to get the exact direction to the enemy
        best_d = my_pos.direction_to(enemy_core_guess)
        
        ##try to step directly toward the enemy
        if best_d and not self.try_step(c, best_d):
            ##if our direct path is blocked (by a wall, ore, or another bot),
            ##sidestep using our wander heading to easily pathfind around it.
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
                        ##miners prioritize Titanium. Refiners prioritize Axionite!
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

        ##drop target if someone built on it (BUT ONLY check if we can actually see it!)
        if self.target_ore and c.is_in_vision(self.target_ore):
            if c.get_tile_building_id(self.target_ore) is not None:
                self.target_ore = None

        if self.target_ore:
            dist = my_pos.distance_squared(self.target_ore)
            ##must be exactly cardinal distance 1 to ensure conveyor connects
            if dist == 1:
                ti, _ = c.get_global_resources()
                scale = c.get_scale_percent() / 100.0
                project_cost = int(80 * scale) + (len(self.history) * int(3 * scale))
                
                if ti >= project_cost and c.can_build_harvester(self.target_ore):
                    c.build_harvester(self.target_ore)
                    self.state = "RETURN" 
                    self.target_ore = None
                else:
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
        
        free_dirs = []
        empty_dirs = []
        
        for check_d in CARDINALS:
            np = my_pos.add(check_d)
            if 0 <= np.x < c.get_map_width() and 0 <= np.y < c.get_map_height():
                ##avoid mindless 1-tile backtracking
                if len(self.history) < 2 or np != self.history[-2]:
                    ##cRUCIAL FIX: can_move actually checks if another bot is blocking us!
                    if c.can_move(check_d): 
                        free_dirs.append(check_d)
                    elif c.is_tile_empty(np) and c.get_tile_building_id(np) is None:
                        empty_dirs.append(check_d)

        ##priority 1: Walk on existing free roads/conveyors
        if d in free_dirs:
            c.move(d)
            self.history.append(my_pos)
            return True
        elif free_dirs:
            ##our preferred direction is blocked, but there is another free road!
            self.heading = random.choice(free_dirs)
            c.move(self.heading)
            self.history.append(my_pos)
            return True
            
        ##priority 2: We reached the end of the road. Pave into the unknown.
        build_dir = None
        if d in empty_dirs:
            build_dir = d
        elif empty_dirs:
            build_dir = random.choice(empty_dirs)
            self.heading = build_dir
            
        if build_dir:
            np = my_pos.add(build_dir)
            ti, _ = c.get_global_resources()
            scale = c.get_scale_percent() / 100.0
            
            if ti >= int(1 * scale) + (15 * scale) and c.can_build_road(np):
                c.build_road(np)
            return True
            
        ##priority 3: We are completely boxed in by bots or walls!
        ##step aside and wait for traffic to clear.
        self._turn()
        if len(self.history) > 1:
            self.history.pop() 
        return False

    def _turn(self):
        ##instead of randomly bouncing, turn left or right 90 degrees cleanly
        idx = CARDINALS.index(self.heading)
        offset = random.choice([-1, 1])
        self.heading = CARDINALS[(idx + offset) % 4]

    def do_return(self, c: Controller):
        if c.get_action_cooldown() > 0 or c.get_move_cooldown() > 0:
            return
            
        my_pos = c.get_position()
        my_building = c.get_tile_building_id(my_pos)
        
        if len(self.history) == 0:
            self.state = "WANDER"
            self.history.append(my_pos)
            return
            
        target_pos = self.history[-1]
        
        ##eARLY CORE ARRIVAL FIX
        ##if our next step is the Core, don't try to cram inside it!
        target_building = c.get_tile_building_id(target_pos)
        if target_building is not None and c.get_entity_type(target_building) == EntityType.CORE:
            d = None
            for cd in CARDINALS:
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
                    ti, _ = c.get_global_resources()
                    scale = c.get_scale_percent() / 100.0
                    if ti < int(3 * scale):
                        return ##wait till we can afford the final piece
                        
                    if my_building is not None and c.get_entity_type(my_building) == EntityType.ROAD:
                        if c.can_destroy(my_pos):
                            c.destroy(my_pos)
                            
                    if c.can_build_conveyor(my_pos, d):
                        c.build_conveyor(my_pos, d)
                    else:
                        return 
            
            ##boom, we delivered the belt to the core! Reset memory instantly.
            self.history = [my_pos]
            self.state = "WANDER"
            return

        ##sTANDARD RETURN LOGIC
        if my_pos == target_pos:
            self.history.pop()
            return

        d = None
        for cd in CARDINALS:
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
            ti, _ = c.get_global_resources()
            scale = c.get_scale_percent() / 100.0
            if ti < int(3 * scale):
                return 
                
            if my_building is not None and c.get_entity_type(my_building) == EntityType.ROAD:
                if c.can_destroy(my_pos):
                    c.destroy(my_pos)
                    
            if c.can_build_conveyor(my_pos, d):
                c.build_conveyor(my_pos, d)
            else:
                return 

        ##if a Wandering bot is in our way, just wait.
        ##their new code forces them to yield to us!
        if c.can_move(d):
            c.move(d)
            self.history.pop()