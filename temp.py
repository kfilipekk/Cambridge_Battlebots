        
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