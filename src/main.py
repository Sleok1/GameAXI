import math
import random
from dataclasses import dataclass, field

import pygame

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60

TILE_SIZE = 32
GRID_WIDTH = 24
GRID_HEIGHT = 14
WORLD_OFFSET = pygame.Vector2(40, 40)

COLOR_BG = (18, 20, 24)
COLOR_FLOOR = (40, 52, 48)
COLOR_GRID = (52, 66, 60)
COLOR_PLAYER = (92, 200, 255)
COLOR_PLAYER_OUTLINE = (20, 60, 90)
COLOR_NPC = (255, 196, 86)
COLOR_NPC_OUTLINE = (60, 40, 12)
COLOR_HUB = (120, 255, 180)
COLOR_NODE = (80, 190, 140)
COLOR_RESOURCE = (220, 160, 120)
COLOR_TEXT = (235, 235, 235)

PLAYER_SPEED = 220.0
NPC_SPEED = 85.0
NPC_WANDER_SPEED = 50.0
NPC_SEPARATION_DISTANCE = 28.0
NPC_ALERT_DISTANCE = 120.0
NPC_INTERACT_DISTANCE = 18.0

DAY_LENGTH = 45.0


@dataclass
class Tile:
    resource: float = 0.0
    node: bool = False


@dataclass
class Player:
    position: pygame.Vector2
    radius: int = 12

    def move(self, direction: pygame.Vector2, dt: float, bounds: pygame.Rect) -> None:
        if direction.length_squared() > 0:
            direction = direction.normalize()
        self.position += direction * PLAYER_SPEED * dt
        self.position.x = max(bounds.left + self.radius, min(bounds.right - self.radius, self.position.x))
        self.position.y = max(bounds.top + self.radius, min(bounds.bottom - self.radius, self.position.y))

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, COLOR_PLAYER, self.position, self.radius)
        pygame.draw.circle(surface, COLOR_PLAYER_OUTLINE, self.position, self.radius, 2)


@dataclass
class Npc:
    name: str
    position: pygame.Vector2
    velocity: pygame.Vector2
    radius: int = 11
    wander_timer: float = 0.0
    energy: float = 100.0
    knowledge: float = 0.0
    inventory: float = 0.0
    target: pygame.Vector2 | None = None
    role: str = "скиталец"

    def update(self, dt: float, world: "World", player: Player) -> None:
        self.energy = max(0.0, self.energy - dt * 1.8)
        self.knowledge = min(100.0, self.knowledge + dt * 0.05)

        if self.energy < 25:
            self.role = "отдых"
            self.target = world.hub_position
        elif self.inventory >= 3:
            self.role = "строитель"
            self.target = world.find_build_site(self.position)
        else:
            self.role = "сборщик"
            self.target = world.find_resource_tile(self.position)

        if self.target:
            to_target = self.target - self.position
            if to_target.length_squared() > 1:
                desired = to_target.normalize() * NPC_SPEED
                self.velocity = self.velocity.lerp(desired, min(1.0, dt * 2.5))
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                angle = random.uniform(0, math.tau)
                self.velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * NPC_WANDER_SPEED
                self.wander_timer = random.uniform(0.8, 1.6)

        self._apply_separation(world.npcs)
        self.position += self.velocity * dt
        self._clamp(world.bounds)

        if self.role == "сборщик":
            world.gather_resource(self)
        elif self.role == "строитель":
            world.build_node(self)
        elif self.role == "отдых":
            world.recover_at_hub(self)

        if self.position.distance_to(player.position) < NPC_ALERT_DISTANCE:
            self.velocity += (player.position - self.position).normalize() * 20 * dt

    def _apply_separation(self, npcs: list["Npc"]) -> None:
        separation = pygame.Vector2()
        for other in npcs:
            if other is self:
                continue
            offset = self.position - other.position
            dist = offset.length()
            if 0 < dist < NPC_SEPARATION_DISTANCE:
                separation += offset.normalize() * (NPC_SEPARATION_DISTANCE - dist)
        if separation.length_squared() > 0:
            self.velocity += separation * 2.5

    def _clamp(self, bounds: pygame.Rect) -> None:
        if self.position.x - self.radius < bounds.left:
            self.position.x = bounds.left + self.radius
        if self.position.x + self.radius > bounds.right:
            self.position.x = bounds.right - self.radius
        if self.position.y - self.radius < bounds.top:
            self.position.y = bounds.top + self.radius
        if self.position.y + self.radius > bounds.bottom:
            self.position.y = bounds.bottom - self.radius

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.circle(surface, COLOR_NPC, self.position, self.radius)
        pygame.draw.circle(surface, COLOR_NPC_OUTLINE, self.position, self.radius, 2)
        label = font.render(self.name, True, COLOR_TEXT)
        surface.blit(label, (self.position.x - label.get_width() / 2, self.position.y - 28))


@dataclass
class World:
    grid: list[list[Tile]] = field(default_factory=list)
    hub_position: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2())
    bounds: pygame.Rect = field(default_factory=pygame.Rect)
    npcs: list[Npc] = field(default_factory=list)
    day_time: float = 0.0
    day_count: int = 1

    def update(self, dt: float) -> None:
        self.day_time += dt
        if self.day_time > DAY_LENGTH:
            self.day_time = 0
            self.day_count += 1

        for row in self.grid:
            for tile in row:
                tile.resource = min(1.0, tile.resource + dt * 0.02)

    def tile_center(self, grid_x: int, grid_y: int) -> pygame.Vector2:
        return WORLD_OFFSET + pygame.Vector2(grid_x * TILE_SIZE + TILE_SIZE / 2, grid_y * TILE_SIZE + TILE_SIZE / 2)

    def find_resource_tile(self, position: pygame.Vector2) -> pygame.Vector2 | None:
        best = None
        best_distance = float("inf")
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.resource < 0.4 or tile.node:
                    continue
                center = self.tile_center(x, y)
                dist = center.distance_to(position)
                if dist < best_distance:
                    best_distance = dist
                    best = center
        return best

    def find_build_site(self, position: pygame.Vector2) -> pygame.Vector2 | None:
        best = None
        best_distance = float("inf")
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.node or tile.resource < 0.2:
                    continue
                center = self.tile_center(x, y)
                dist = center.distance_to(position)
                if dist < best_distance:
                    best_distance = dist
                    best = center
        return best

    def gather_resource(self, npc: Npc) -> None:
        grid_x, grid_y = self.world_to_grid(npc.position)
        if grid_x is None:
            return
        tile = self.grid[grid_y][grid_x]
        if tile.resource > 0.2:
            tile.resource = max(0.0, tile.resource - 0.3)
            npc.inventory += 1

    def build_node(self, npc: Npc) -> None:
        grid_x, grid_y = self.world_to_grid(npc.position)
        if grid_x is None:
            return
        tile = self.grid[grid_y][grid_x]
        if not tile.node and npc.inventory >= 3 and tile.resource > 0.2:
            tile.node = True
            npc.inventory -= 3
            npc.knowledge = min(100.0, npc.knowledge + 8)

    def recover_at_hub(self, npc: Npc) -> None:
        if npc.position.distance_to(self.hub_position) < NPC_INTERACT_DISTANCE:
            npc.energy = min(100.0, npc.energy + 35)

    def world_to_grid(self, position: pygame.Vector2) -> tuple[int | None, int | None]:
        local = position - WORLD_OFFSET
        if local.x < 0 or local.y < 0:
            return None, None
        grid_x = int(local.x // TILE_SIZE)
        grid_y = int(local.y // TILE_SIZE)
        if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
            return grid_x, grid_y
        return None, None


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("GameAXI: Tron Micro World")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 16)
        self.big_font = pygame.font.SysFont("arial", 26, bold=True)
        self.player = Player(position=self._world_center())
        self.world = self._create_world()
        self.running = True

    def _world_center(self) -> pygame.Vector2:
        return WORLD_OFFSET + pygame.Vector2(GRID_WIDTH * TILE_SIZE / 2, GRID_HEIGHT * TILE_SIZE / 2)

    def _create_world(self) -> World:
        grid = []
        for _ in range(GRID_HEIGHT):
            row = []
            for _ in range(GRID_WIDTH):
                row.append(Tile(resource=random.uniform(0.1, 0.8)))
            grid.append(row)
        bounds = pygame.Rect(
            WORLD_OFFSET.x,
            WORLD_OFFSET.y,
            GRID_WIDTH * TILE_SIZE,
            GRID_HEIGHT * TILE_SIZE,
        )
        hub_pos = WORLD_OFFSET + pygame.Vector2(TILE_SIZE * 3, TILE_SIZE * 3)
        npcs = [
            Npc(name="Эхо", position=hub_pos + pygame.Vector2(120, 40), velocity=pygame.Vector2(40, 10)),
            Npc(name="Люм", position=hub_pos + pygame.Vector2(40, 180), velocity=pygame.Vector2(-20, 50)),
            Npc(name="Код", position=hub_pos + pygame.Vector2(220, 140), velocity=pygame.Vector2(30, -40)),
        ]
        return World(grid=grid, hub_position=hub_pos, bounds=bounds, npcs=npcs)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            self._update(dt)
            self._draw()

        pygame.quit()

    def _update(self, dt: float) -> None:
        self.world.update(dt)
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        self.player.move(direction, dt, self.world.bounds)

        for npc in self.world.npcs:
            npc.update(dt, self.world, self.player)

    def _draw(self) -> None:
        self.screen.fill(COLOR_BG)
        pygame.draw.rect(self.screen, COLOR_FLOOR, self.world.bounds)

        for y, row in enumerate(self.world.grid):
            for x, tile in enumerate(row):
                center = self.world.tile_center(x, y)
                rect = pygame.Rect(
                    center.x - TILE_SIZE / 2,
                    center.y - TILE_SIZE / 2,
                    TILE_SIZE,
                    TILE_SIZE,
                )
                if tile.resource > 0.65:
                    pygame.draw.rect(self.screen, COLOR_RESOURCE, rect)
                if tile.node:
                    pygame.draw.rect(self.screen, COLOR_NODE, rect)

        for x in range(GRID_WIDTH + 1):
            start = WORLD_OFFSET + pygame.Vector2(x * TILE_SIZE, 0)
            end = WORLD_OFFSET + pygame.Vector2(x * TILE_SIZE, GRID_HEIGHT * TILE_SIZE)
            pygame.draw.line(self.screen, COLOR_GRID, start, end, 1)
        for y in range(GRID_HEIGHT + 1):
            start = WORLD_OFFSET + pygame.Vector2(0, y * TILE_SIZE)
            end = WORLD_OFFSET + pygame.Vector2(GRID_WIDTH * TILE_SIZE, y * TILE_SIZE)
            pygame.draw.line(self.screen, COLOR_GRID, start, end, 1)

        pygame.draw.circle(self.screen, COLOR_HUB, self.world.hub_position, 18)
        pygame.draw.circle(self.screen, (40, 90, 60), self.world.hub_position, 18, 2)

        for npc in self.world.npcs:
            npc.draw(self.screen, self.font)

        self.player.draw(self.screen)

        self._draw_hud()
        pygame.display.flip()

    def _draw_hud(self) -> None:
        day_progress = self.world.day_time / DAY_LENGTH
        bar_width = 200
        bar_rect = pygame.Rect(40, SCREEN_HEIGHT - 44, bar_width, 10)
        pygame.draw.rect(self.screen, (60, 60, 70), bar_rect)
        pygame.draw.rect(self.screen, (140, 180, 255), (bar_rect.x, bar_rect.y, bar_width * day_progress, 10))

        title = self.big_font.render("Мир ИИ", True, COLOR_TEXT)
        status = self.font.render(
            f"День {self.world.day_count}  |  NPC: {len(self.world.npcs)}  |  Узлы: {self._count_nodes()}",
            True,
            COLOR_TEXT,
        )
        hint = self.font.render("WASD/стрелки — движение. NPC сами собирают ресурсы и строят узлы.", True, COLOR_TEXT)
        self.screen.blit(title, (40, SCREEN_HEIGHT - 90))
        self.screen.blit(status, (40, SCREEN_HEIGHT - 68))
        self.screen.blit(hint, (40, SCREEN_HEIGHT - 24))

    def _count_nodes(self) -> int:
        return sum(1 for row in self.world.grid for tile in row if tile.node)


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
