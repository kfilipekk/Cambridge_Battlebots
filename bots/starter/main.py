"""Starter bot - a simple example to demonstrate usage of the Controller API.

Each unit gets its own Player instance; the engine calls run() once per round.
Use Controller.get_entity_type() to branch on what kind of unit you are.

This bot:
  - Core: spawns up to 3 builder bots on random adjacent tiles
  - Builder bot: builds a harvester on any adjacent ore tile, then moves in a
    random direction (laying a road first so the tile is passable), and places
    a marker recording the current round number
"""

import random
import sys
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
        
    def run(self, c: Controller) -> None:
        etype = c.get_entity_type()
        if etype == EntityType.CORE:
            self.run_core(c)
        elif etype == EntityType.BUILDER_BOT:
            self.run_builder(c)

    def run_core(self, c: Controller):
        ##prevent economic collapse by limiting bots. Scale hits us +10% per bot!
        if self.spawned_bots < 8 and c.get_action_cooldown() == 0:
            ti, ax = c.get_global_resources()
            scale = c.get_scale_percent() / 100.0
            builder_cost = int(10 * scale)
            
            ##ensure we maintain a titanium buffer to build continuous roads/conveyors
            if ti > builder_cost + 40:
                spawn_dirs = list(CARDINALS)
                random.shuffle(spawn_dirs)
                for d in spawn_dirs:
                    target = c.get_position().add(d)
                    if c.can_spawn(target):
                        c.spawn_builder(target)
                        self.spawned_bots += 1
                        break

    def run_builder(self, c: Controller):
        if self.state == "INIT":
            self.state = "WANDER"
            self.heading = random.choice(CARDINALS)
            self.history.append(c.get_position())

        if self.state == "WANDER":
            self.do_wander(c)
        elif self.state == "RETURN":
            self.do_return(c)
            
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
                        dist = my_pos.distance_squared(tile)
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
            ##action radius allows us to build from slightly further, but strictly speaking 2 dist is ideal
            if dist <= 2:
                if c.can_build_harvester(self.target_ore):
                    print(f"[{c.get_id()}] Building harvester at {self.target_ore}", file=sys.stderr)
                    c.build_harvester(self.target_ore)
                    self.state = "RETURN" 
                    self.target_ore = None
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
                    self.try_step(c, best_d)
                return
                
        next_pos = my_pos.add(self.heading)
        ##check map bounds before querying tiles to avoid GameError
        if (next_pos.x < 0 or next_pos.x >= c.get_map_width() or
            next_pos.y < 0 or next_pos.y >= c.get_map_height()):
            self.heading = random.choice(CARDINALS)
        elif not c.is_tile_passable(next_pos) and not c.is_tile_empty(next_pos):
            self.heading = random.choice(CARDINALS)
        
        self.try_step(c, self.heading)

    def try_step(self, c: Controller, d: Direction):
        my_pos = c.get_position()
        next_pos = my_pos.add(d)
        
        if (next_pos.x < 0 or next_pos.x >= c.get_map_width() or
            next_pos.y < 0 or next_pos.y >= c.get_map_height()):
            self.heading = random.choice(CARDINALS)
            return

        if not c.is_tile_passable(next_pos):
            if c.is_tile_empty(next_pos):
                if c.can_build_road(next_pos):
                    c.build_road(next_pos)
                return 
            else:
                self.heading = random.choice(CARDINALS)
                return

        if c.can_move(d):
            ##prevent mindless backtracking
            if self.history and self.history[-1] == next_pos:
                self.heading = random.choice(CARDINALS)
                return
            c.move(d)
            self.history.append(my_pos) 

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
                return ###can't afford it yet, halt and wait

        if c.can_move(d):
            c.move(d)
            self.history.pop()
