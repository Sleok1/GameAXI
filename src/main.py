import random
from dataclasses import dataclass
from typing import Tuple

import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FLOOR_HEIGHT = 140
BG_COLOR = (22, 24, 28)
FLOOR_COLOR = (64, 80, 72)
NPC_COLOR = (255, 196, 86)
NPC_OUTLINE = (40, 28, 14)


@dataclass
class Npc:
    position: pygame.Vector2
    velocity: pygame.Vector2
    radius: int
    wander_timer: float

    def update(self, dt: float, bounds: pygame.Rect) -> None:
        self.wander_timer -= dt
        if self.wander_timer <= 0:
            angle = random.uniform(0, 360)
            speed = random.uniform(30, 90)
            self.velocity = pygame.Vector2(speed, 0).rotate(angle)
            self.wander_timer = random.uniform(0.8, 2.0)

        self.position += self.velocity * dt

        if self.position.x - self.radius < bounds.left:
            self.position.x = bounds.left + self.radius
            self.velocity.x *= -1
        if self.position.x + self.radius > bounds.right:
            self.position.x = bounds.right - self.radius
            self.velocity.x *= -1
        if self.position.y - self.radius < bounds.top:
            self.position.y = bounds.top + self.radius
            self.velocity.y *= -1
        if self.position.y + self.radius > bounds.bottom:
            self.position.y = bounds.bottom - self.radius
            self.velocity.y *= -1

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, NPC_COLOR, self.position, self.radius)
        pygame.draw.circle(surface, NPC_OUTLINE, self.position, self.radius, 2)


def create_npc(start: Tuple[int, int]) -> Npc:
    velocity = pygame.Vector2(random.uniform(-50, 50), random.uniform(-50, 50))
    return Npc(position=pygame.Vector2(start), velocity=velocity, radius=18, wander_timer=0.0)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("GameAXI: NPC Playground")
    clock = pygame.time.Clock()

    play_area = pygame.Rect(40, 40, SCREEN_WIDTH - 80, SCREEN_HEIGHT - FLOOR_HEIGHT - 60)
    npcs = [create_npc((200, 200)), create_npc((520, 260))]

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for npc in npcs:
            npc.update(dt, play_area)

        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, FLOOR_COLOR, (0, SCREEN_HEIGHT - FLOOR_HEIGHT, SCREEN_WIDTH, FLOOR_HEIGHT))
        pygame.draw.rect(screen, (90, 110, 100), play_area, 2)

        for npc in npcs:
            npc.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
