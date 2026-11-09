import sys
import os
import pygame
import requests

API_BASE_URL = "http://127.0.0.1:8000"

COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)
COLOR_PRESENT = (181, 159, 59)
COLOR_ABSENT = (58, 58, 60)
COLOR_LINE = (70, 70, 75)

pygame.init()
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)
history_font = pygame.font.SysFont("Arial", 20, bold=True)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.hard_mode = False
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, R to restart, H to toggle Hard Mode"
        self.history_words = []
        self.stats = {"total_games": 0, "wins": 0, "win_rate": 0.0}
        self.start_new_game()

    def fetch_stats(self):
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=5)
            if res.status_code == 200:
                self.stats = res.json()
        except requests.exceptions.RequestException:
            pass

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局（支援 hard_mode） """
        try:
            res = requests.post(f"{API_BASE_URL}/api/new-game?hard_mode={str(self.hard_mode).lower()}", timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.history_words = []
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! Mode: {mode_str}"
                self.fetch_stats()
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def toggle_hard_mode(self):
        self.hard_mode = not self.hard_mode
        self.start_new_game()

    def submit_guess(self):
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)

            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]

                self.history_words.append(guess_word)

                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press SPACE to restart."
                    self.game_over = True
                    self.fetch_stats()
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6:
                        target = data.get("target_word", "UNKNOWN")

                        self.message = f"Game Over! The word was {target}. Press SPACE to restart."
                        self.game_over = True
                        self.fetch_stats()
                    else:

                        tries_left = 6 - self.row
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                detail = res.json().get("detail", "Error processing guess")

                if detail == "Word not in dictionary":
                    self.message = "Not in word list!"
                else:
                    self.message = detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_SPACE:
            self.start_new_game()
            return
        if event.key == pygame.K_TAB:
            self.toggle_hard_mode()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)

        margin_x, margin_y = 45, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)

                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        panel_x = 500
        pygame.draw.line(surface, COLOR_LINE, (panel_x, 0), (panel_x, HEIGHT - 80), 2)

        stats_text1 = f"Total: {self.stats['total_games']} | Wins: {self.stats['wins']}"
        stats_text2 = f"Win Rate: {self.stats['win_rate']}%"

        surface.blit(small_font.render(stats_text1, True, COLOR_TEXT), (panel_x + 10, 20))
        surface.blit(small_font.render(stats_text2, True, COLOR_TEXT), (panel_x + 10, 45))

        mode_text = f"Mode: {'HARD' if self.hard_mode else 'Normal'}"
        mode_color = (255, 100, 100) if self.hard_mode else (100, 255, 100)
        mode_surface = small_font.render(mode_text, True, mode_color)
        surface.blit(mode_surface, (panel_x + 10, 70))

        history_title = small_font.render("Guess History:", True, (180, 180, 180))
        surface.blit(history_title, (panel_x + 15, 90))

        for idx, word in enumerate(self.history_words):
            w_surface = history_font.render(f"{idx + 1}. {word}", True, COLOR_TEXT)
            surface.blit(w_surface, (panel_x + 15, 120 + idx * 35))

        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)

def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
