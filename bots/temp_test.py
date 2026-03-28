from cambc import Controller, EntityType
class Player:
    def run(self, c: Controller):
        print("LAUNCHER COST:", c.get_launcher_cost())
        print("GUNNER COST:", c.get_gunner_cost())
        print("SENTINEL COST:", c.get_sentinel_cost())
        print("BREACH COST:", c.get_breach_cost())
        print("BARRIER COST:", c.get_barrier_cost())
