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
        
        dynamic_bot_cap = min(25, 6 + int(ti / 400))
        
        if self.spawned_bots < dynamic_bot_cap:
            builder_cost = int(10 * scale)
            harvester_cost = int(80 * scale)
            
            ##iNCREASED BUFFER: Keep 100 Ti in reserve for active conveyor projects
            if ti > builder_cost + harvester_cost + (100 * scale):
                spawn_dirs = list(CARDINALS)
                random.shuffle(spawn_dirs)
                for d in spawn_dirs:
                    target = c.get_position().add(d)
                    if c.can_spawn(target):
                        c.spawn_builder(target)
                        self.spawned_bots += 1
                        break

    def check_and_build_foundry(self, c: Controller):
        ##eCONOMY CHECK
        ti, ax = c.get_global_resources()
        scale = c.get_scale_percent() / 100.0
        
        ##foundry base is 120. We want a MASSIVE buffer (e.g., 500 Ti)
        ##so doubling our scaling doesn't instantly bankrupt us.
        if ti < (120 * scale) + 500: 
            return False
            
        ##we need Raw Axionite to actually use the Foundry, so don't build it too early
        if ax < 10:
            return False

        core_pos = self.history[0] if self.history else c.get_position()
        
        ##mARKER CHECK (The Radio Broadcast)
        ##scan all nearby entities to see if a marker with our secret code exists
        foundry_claimed = False
        for eid in c.get_nearby_entities():
            try:
                ##safely check if this entity is a marker and read it
                if c.get_entity_type(eid) == getattr(EntityType, 'MARKER', None):
                    if c.get_marker_value(eid) == 999:
                        foundry_claimed = True
                        break
            except Exception:
                pass
                
        ##pHYSICAL FAILSAFE (Look with our eyes)
        ##just in case the marker was destroyed by an enemy or a glitch
        for tile in c.get_nearby_tiles(25):
            bid = c.get_tile_building_id(tile)
            if bid and c.get_entity_type(bid) == getattr(EntityType, 'AXIONITE_FOUNDRY', None):
                foundry_claimed = True
                break

        if foundry_claimed:
            return False ##someone else is handling it. Abort!
            
        ##cLAIM IT AND BUILD
        ##drop the marker to claim the job
        if hasattr(c, 'can_place_marker') and c.can_place_marker(core_pos):
            c.place_marker(core_pos, 999)
            
        ##find an empty tile near the core to build it safely behind our lines
        for d in CARDINALS:
            build_pos = core_pos.add(d)
            if c.is_tile_empty(build_pos):
                ##the API pattern matches the building name
                if hasattr(c, 'can_build_axionite_foundry') and c.can_build_axionite_foundry(build_pos):
                    c.build_axionite_foundry(build_pos)
                    return True
                    
        return False

    def run_builder(self, c: Controller):
        if self.state == "INIT":
            self.state = "WANDER"
            self.history.append(c.get_position())
            
            ##roles: 80% Miners, 20% Saboteurs
            if random.random() < 0.2 and c.get_current_round() > 300:
                self.role = "SABOTEUR"
            else:
                self.role = "MINER"
            
            ##sCATTER PROTOCOL: When spawning, try to pick a direction that DOES NOT have a conveyor
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
            ##---> NEW: Check if we should stop and build a Foundry! <---
            if self.check_and_build_foundry(c):
                return ##we spent our action building the Foundry, end turn

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

        ##dROP TURRETS: If we are close to the target, start shooting!
        ##if we are within 12 tiles of the calculated enemy core, we are in the hot zone
        if my_pos.distance_squared(enemy_core_guess) < 144: 
            ti, _ = c.get_global_resources()
            scale = c.get_scale_percent() / 100.0
            gunner_cost = int(10 * scale)
            
            if ti > gunner_cost + 50: ##leave a buffer so we don't drain the economy
                for d in CARDINALS:
                    build_target = my_pos.add(d)
                    if c.can_build_gunner(build_target, d):
                        c.build_gunner(build_target, d)
                        ##self-destruct after placing a turret to do 20 damage to anything nearby!
                        c.self_destruct() 
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
                        dist_penalty = -99999 if env == Environment.ORE_AXIONITE else 0
                        ##ensure we don't try to place harvesters ON the map squares underneath our own 3x3 core footprint
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
        
        ##drop target if someone built on it before we got there
        if self.target_ore and c.get_tile_building_id(self.target_ore) is not None:
            self.target_ore = None

        if self.target_ore:
            dist = my_pos.distance_squared(self.target_ore)
            if dist <= 2:
                ##check if we can afford the Harvester AND the conveyor belt back!
                ti, _ = c.get_global_resources()
                scale = c.get_scale_percent() / 100.0
                project_cost = int(80 * scale) + (len(self.history) * int(3 * scale))
                
                if ti >= project_cost and c.can_build_harvester(self.target_ore):
                    c.build_harvester(self.target_ore)
                    self.state = "RETURN" 
                    self.target_ore = None
                else:
                    ##we can't afford the FULL project yet. Step aside and wait!
                    self._turn()
                    self.try_step(c, self.heading)
                return
            else:
                ##seek ore ONLY using Cardinals so it matches conveyor directions!
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
                
        ##move in straight lines based on the current heading
        self.try_step(c, self.heading)

    def try_step(self, c: Controller, d: Direction):
        my_pos = c.get_position()
        next_pos = my_pos.add(d)
        
        ##bounds Check
        if (next_pos.x < 0 or next_pos.x >= c.get_map_width() or
            next_pos.y < 0 or next_pos.y >= c.get_map_height()):
            self._turn()
            return False

        ##path Check
        if not c.is_tile_passable(next_pos):
            if c.is_tile_empty(next_pos):
                ti, _ = c.get_global_resources()
                scale = c.get_scale_percent() / 100.0
                road_cost = int(1 * scale)
                
                ##rEQUIRE A BUFFER OF 15 Ti: Don't build roads if it starves returning bots!
                if ti >= road_cost + (15 * scale) and c.can_build_road(next_pos):
                    c.build_road(next_pos)
                return True 
            else:
                ##hit a wall or building, turn 90 degrees cleanly
                self._turn()
                return False

        ##move and Record History
        if c.can_move(d):
            if next_pos in self.history:
                idx = self.history.index(next_pos)
                self.history = self.history[:idx+1]
            else:
                self.history.append(my_pos)
                
            c.move(d)
            return True 
        else:
            ##---> TRAFFIC JAM FIX <---
            ##the tile is passable, but we can't move. Another bot is blocking us!
            ##turn 90 degrees to sidestep them.
            self._turn()
            return False

    def _turn(self):
        ##instead of randomly bouncing, turn left or right 90 degrees cleanly
        idx = CARDINALS.index(self.heading)
        offset = random.choice([-1, 1])
        self.heading = CARDINALS[(idx + offset) % 4]

    def do_return(self, c: Controller):
        if c.get_action_cooldown() > 0 or c.get_move_cooldown() > 0:
            return
            
        if len(self.history) == 0:
            self.state = "WANDER"
            self.history.append(c.get_position())
            return
            
        my_pos = c.get_position()
        target_pos = self.history[-1]
        
        if my_pos == target_pos:
            self.history.pop()
            return

        ##explicitly find which Cardinal matches our history regression
        d = None
        for cd in CARDINALS:
            if my_pos.add(cd) == target_pos:
                d = cd
                break
                
        if d is None:
            self.history.pop()
            return

        my_building = c.get_tile_building_id(my_pos)
        needs_conveyor = True
        
        if my_building is not None:
            b_type = c.get_entity_type(my_building)
            ##destroy our old road freely to place a conveyor
            if b_type == EntityType.ROAD:
                if c.can_destroy(my_pos):
                    c.destroy(my_pos)
            elif b_type in (EntityType.CONVEYOR, EntityType.ARMOURED_CONVEYOR):
                needs_conveyor = False
            elif b_type in (EntityType.CORE, EntityType.HARVESTER):
                needs_conveyor = False

        if needs_conveyor:
            if c.can_build_conveyor(my_pos, d):
                c.build_conveyor(my_pos, d)
            else:
                return ##can't afford it yet, halt and wait

        if c.can_move(d):
            c.move(d)
            self.history.pop()