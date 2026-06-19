import random
import tkinter as tk
from tkinter import messagebox
from collections import deque


GRID_SIZE = 4
MAX_STEPS = 100

DIRECTIONS = ["East", "South", "West", "North"]

MOVE_DELTA = {
    "East": (1, 0),
    "South": (0, -1),
    "West": (-1, 0),
    "North": (0, 1),
}


# =====================================
# 환경 클래스
# =====================================

class Environment:
    def __init__(self):
        self.size = GRID_SIZE
        self.start = (1, 1)

        self.gold = None
        self.wumpus = None
        self.pits = set()

        self.wumpus_alive = True
        self.gold_taken = False
        self.agent_dead = False
        self.game_success = False

        self.generate_world()

    def generate_world(self):
        """
        Wumpus, Pit, Gold의 위치를 생성한다.
        시작 위치 (1,1)은 항상 안전하다.
        """

        cells = [
            (x, y)
            for x in range(1, self.size + 1)
            for y in range(1, self.size + 1)
            if (x, y) != self.start
        ]

        # 시작 위치 근처에는 위험 요소를 배치하지 않는다.
        start_neighbors = {(1, 2), (2, 1)}

        wumpus_cells = [
            cell
            for cell in cells
            if cell not in start_neighbors
        ]

        self.wumpus = random.choice(wumpus_cells)

        # 각 칸에 0.10 확률로 Pit을 생성한다.
        for cell in cells:
            if cell == self.wumpus or cell in start_neighbors:
                continue

            if random.random() < 0.10:
                self.pits.add(cell)

        # Gold는 Wumpus 또는 Pit과 겹치지 않는다.
        gold_cells = [
            cell
            for cell in cells
            if cell != self.wumpus and cell not in self.pits
        ]

        self.gold = random.choice(gold_cells)

    def in_bounds(self, cell):
        """
        좌표가 4×4 지도 안에 있는지 확인한다.
        """

        x, y = cell

        return (
            1 <= x <= self.size
            and 1 <= y <= self.size
        )

    def adjacent_cells(self, cell):
        """
        현재 칸의 상하좌우 인접 칸을 반환한다.
        """

        x, y = cell

        candidates = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        return [
            candidate
            for candidate in candidates
            if self.in_bounds(candidate)
        ]

    def get_percept(self, agent):
        """
        다섯 가지 감지 정보를 생성한다.

        Stench
        Breeze
        Glitter
        Bump
        Scream
        """

        adjacent = self.adjacent_cells(agent.position)

        percept = {
            "Stench": (
                self.wumpus_alive
                and self.wumpus in adjacent
            ),
            "Breeze": any(
                pit in adjacent
                for pit in self.pits
            ),
            "Glitter": (
                agent.position == self.gold
                and not self.gold_taken
            ),
            "Bump": agent.bump,
            "Scream": agent.scream,
        }

        # Bump와 Scream은 한 번만 사용되는 감지 정보이다.
        agent.bump = False
        agent.scream = False

        return percept

    def execute_action(self, agent, action):
        """
        에이전트가 선택한 행동을 실행한다.
        """

        if action == "TurnLeft":
            agent.turn_left()

            return (
                "에이전트가 왼쪽으로 회전했습니다. "
                f"현재 방향: {agent.direction}"
            )

        if action == "TurnRight":
            agent.turn_right()

            return (
                "에이전트가 오른쪽으로 회전했습니다. "
                f"현재 방향: {agent.direction}"
            )

        if action == "GoForward":
            dx, dy = MOVE_DELTA[agent.direction]

            new_position = (
                agent.position[0] + dx,
                agent.position[1] + dy,
            )

            if not self.in_bounds(new_position):
                agent.bump = True

                return (
                    "에이전트가 벽에 부딪혔습니다. "
                    "위치는 변하지 않습니다."
                )

            old_position = agent.position
            agent.position = new_position

            result = (
                f"에이전트가 {old_position}에서 "
                f"{new_position}(으)로 이동했습니다."
            )

            if new_position in self.pits:
                self.agent_dead = True
                result += " 에이전트가 Pit에 빠졌습니다. 임무 실패."

            elif (
                new_position == self.wumpus
                and self.wumpus_alive
            ):
                self.agent_dead = True
                result += " 에이전트가 Wumpus에게 잡혔습니다. 임무 실패."

            return result

        if action == "Grab":
            if (
                agent.position == self.gold
                and not self.gold_taken
            ):
                self.gold_taken = True
                agent.has_gold = True

                return (
                    "에이전트가 Gold를 획득했습니다. "
                    "이제 시작 위치 (1,1)로 돌아갑니다."
                )

            return "현재 위치에는 Gold가 없습니다."

        if action == "Shoot":
            if agent.arrows <= 0:
                return "남아 있는 화살이 없습니다."

            agent.arrows -= 1

            return self.shoot_arrow(agent)

        if action == "Climb":
            if (
                agent.position == self.start
                and agent.has_gold
            ):
                self.game_success = True

                return (
                    "에이전트가 Gold를 가지고 (1,1)로 돌아와 "
                    "Climb을 실행했습니다. 임무 성공!"
                )

            return (
                "Gold를 획득한 후 (1,1)로 돌아와야 "
                "Climb을 실행할 수 있습니다."
            )

        return f"알 수 없는 행동입니다: {action}"

    def shoot_arrow(self, agent):
        """
        현재 방향으로 화살을 발사한다.
        화살 경로에 Wumpus가 있으면 Wumpus를 제거한다.
        """

        dx, dy = MOVE_DELTA[agent.direction]
        x, y = agent.position

        while True:
            x += dx
            y += dy

            current = (x, y)

            if not self.in_bounds(current):
                return "화살이 Wumpus를 맞히지 못했습니다."

            if (
                current == self.wumpus
                and self.wumpus_alive
            ):
                self.wumpus_alive = False
                agent.scream = True

                return (
                    "화살이 Wumpus를 맞혔습니다. "
                    "Scream이 들렸습니다."
                )


# =====================================
# 에이전트 클래스
# =====================================

class Agent:
    def __init__(self):
        self.position = (1, 1)
        self.direction = "East"

        self.arrows = 3
        self.has_gold = False

        # 지식 베이스
        self.visited = {(1, 1)}
        self.safe = {(1, 1)}
        self.possible_pit = set()
        self.possible_wumpus = set()

        # 일회성 감지 정보
        self.bump = False
        self.scream = False

    def adjacent_cells(self, cell):
        """
        현재 칸의 인접 칸을 반환한다.
        """

        x, y = cell

        candidates = [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
        ]

        return [
            candidate
            for candidate in candidates
            if (
                1 <= candidate[0] <= GRID_SIZE
                and 1 <= candidate[1] <= GRID_SIZE
            )
        ]

    def update_knowledge(self, percept):
        """
        감지 정보를 사용하여 지식 베이스를 업데이트한다.
        """

        self.visited.add(self.position)
        self.safe.add(self.position)

        adjacent = self.adjacent_cells(self.position)

        # Breeze와 Stench가 없으면 인접 칸은 안전하다.
        if (
            not percept["Breeze"]
            and not percept["Stench"]
        ):
            for cell in adjacent:
                self.safe.add(cell)
                self.possible_pit.discard(cell)
                self.possible_wumpus.discard(cell)

        # Breeze가 있으면 인접 칸에 Pit이 있을 가능성이 있다.
        if percept["Breeze"]:
            for cell in adjacent:
                if (
                    cell not in self.visited
                    and cell not in self.safe
                ):
                    self.possible_pit.add(cell)

        # Stench가 있으면 인접 칸에 Wumpus가 있을 가능성이 있다.
        if percept["Stench"]:
            for cell in adjacent:
                if (
                    cell not in self.visited
                    and cell not in self.safe
                ):
                    self.possible_wumpus.add(cell)

        # Scream이 들리면 Wumpus가 제거된 것이다.
        if percept["Scream"]:
            self.possible_wumpus.clear()

    def choose_action(self, percept):
        """
        현재 감지 정보와 지식 베이스를 바탕으로
        다음 행동을 선택한다.
        """

        # 현재 위치에 Gold가 있으면 획득한다.
        if percept["Glitter"]:
            return "Grab"

        # Gold를 가지고 시작 위치로 돌아오면 탈출한다.
        if (
            self.has_gold
            and self.position == (1, 1)
        ):
            return "Climb"

        # Gold를 획득한 후 BFS로 시작 위치에 돌아간다.
        if self.has_gold:
            path = self.find_path(
                self.position,
                (1, 1),
            )

            if path and len(path) > 1:
                return self.move_toward(path[1])

            return "TurnRight"

        # 안전하고 아직 방문하지 않은 칸을 찾는다.
        safe_unvisited = [
            cell
            for cell in self.safe
            if (
                cell not in self.visited
                and cell not in self.possible_pit
                and cell not in self.possible_wumpus
            )
        ]

        target = self.find_nearest_reachable(
            safe_unvisited
        )

        if target is not None:
            path = self.find_path(
                self.position,
                target,
            )

            if path and len(path) > 1:
                return self.move_toward(path[1])

        # Stench가 있고 화살이 있으면 발사한다.
        if (
            percept["Stench"]
            and self.arrows > 0
        ):
            return "Shoot"

        # 안전한 칸이 없으면 가장 위험도가 낮은 칸을 선택한다.
        risky_target = self.choose_lowest_risk_neighbor()

        if risky_target is not None:
            return self.move_toward(risky_target)

        # 새로운 칸이 없으면 시작 위치로 돌아간다.
        path = self.find_path(
            self.position,
            (1, 1),
        )

        if path and len(path) > 1:
            return self.move_toward(path[1])

        return "TurnRight"

    def choose_lowest_risk_neighbor(self):
        """
        이동 가능한 안전한 칸이 없을 때
        가장 위험도가 낮은 인접 칸을 선택한다.
        """

        candidates = []

        for cell in self.adjacent_cells(self.position):
            if cell in self.visited:
                continue

            risk = 0

            if cell in self.possible_pit:
                risk += 2

            if cell in self.possible_wumpus:
                risk += 2

            candidates.append((risk, cell))

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return candidates[0][1]

    def find_path(self, start, goal):
        """
        BFS를 사용하여 이미 알고 있는 안전한 칸 사이에서
        경로를 탐색한다.
        """

        safe_cells = {
            cell
            for cell in self.safe
            if (
                cell not in self.possible_pit
                and cell not in self.possible_wumpus
            )
        }

        safe_cells.add(start)

        if goal not in safe_cells:
            return None

        queue = deque([
            (start, [start])
        ])

        seen = {start}

        while queue:
            current, path = queue.popleft()

            if current == goal:
                return path

            for neighbor in self.adjacent_cells(current):
                if (
                    neighbor in safe_cells
                    and neighbor not in seen
                ):
                    seen.add(neighbor)

                    queue.append(
                        (
                            neighbor,
                            path + [neighbor],
                        )
                    )

        return None

    def find_nearest_reachable(self, targets):
        """
        BFS로 도달할 수 있는 가장 가까운 목표 칸을 선택한다.
        """

        best_target = None
        best_length = None

        for target in targets:
            path = self.find_path(
                self.position,
                target,
            )

            if path is None:
                continue

            if (
                best_length is None
                or len(path) < best_length
            ):
                best_target = target
                best_length = len(path)

        return best_target

    def move_toward(self, target):
        """
        목표 칸 방향으로 이동한다.
        """

        x, y = self.position
        target_x, target_y = target

        if target_x > x:
            desired = "East"

        elif target_x < x:
            desired = "West"

        elif target_y > y:
            desired = "North"

        else:
            desired = "South"

        return self.turn_or_forward(desired)

    def turn_or_forward(self, desired):
        """
        현재 방향이 목표 방향과 같으면 전진하고,
        다르면 먼저 회전한다.
        """

        if self.direction == desired:
            return "GoForward"

        current_index = DIRECTIONS.index(
            self.direction
        )

        target_index = DIRECTIONS.index(
            desired
        )

        difference = (
            target_index - current_index
        ) % 4

        if difference == 1:
            return "TurnRight"

        return "TurnLeft"

    def turn_left(self):
        index = DIRECTIONS.index(
            self.direction
        )

        self.direction = DIRECTIONS[
            (index - 1) % 4
        ]

    def turn_right(self):
        index = DIRECTIONS.index(
            self.direction
        )

        self.direction = DIRECTIONS[
            (index + 1) % 4
        ]


# =====================================
# 그래픽 사용자 인터페이스
# =====================================

class WumpusWorldUI:
    def __init__(self, root):
        self.root = root

        self.root.title(
            "Wumpus World 지능형 에이전트 시스템"
        )

        self.env = Environment()
        self.agent = Agent()

        self.step_count = 0
        self.game_over = False
        self.auto_running = False

        self.show_real_world = tk.BooleanVar(
            value=True
        )

        self.cells = {}

        self.create_widgets()
        self.update_ui()

        self.log(
            "Wumpus World가 초기화되었습니다."
        )

        self.log(
            "목표: Gold를 찾고 (1,1)로 돌아와 "
            "Climb을 실행합니다."
        )

    def create_widgets(self):
        """
        UI 구성 요소를 생성한다.
        """

        grid_frame = tk.Frame(
            self.root,
            padx=10,
            pady=10,
        )

        grid_frame.grid(
            row=0,
            column=0,
            sticky="n",
        )

        # 4×4 지도
        for y in range(
            GRID_SIZE,
            0,
            -1,
        ):
            for x in range(
                1,
                GRID_SIZE + 1,
            ):
                label = tk.Label(
                    grid_frame,
                    text="?",
                    width=8,
                    height=4,
                    relief="ridge",
                    borderwidth=2,
                    font=(
                        "Arial",
                        14,
                        "bold",
                    ),
                    bg="#f6f1df",
                )

                label.grid(
                    row=GRID_SIZE - y,
                    column=x - 1,
                    padx=3,
                    pady=3,
                )

                self.cells[(x, y)] = label

        # 상태 정보 영역
        info_frame = tk.Frame(
            self.root,
            padx=10,
            pady=10,
        )

        info_frame.grid(
            row=0,
            column=1,
            sticky="n",
        )

        self.status_label = tk.Label(
            info_frame,
            text="",
            justify="left",
            anchor="w",
            width=48,
            font=("Arial", 11),
        )

        self.status_label.pack(
            anchor="w"
        )

        tk.Checkbutton(
            info_frame,
            text="실제 지도 표시 (발표용)",
            variable=self.show_real_world,
            command=self.update_ui,
        ).pack(
            anchor="w",
            pady=5,
        )

        tk.Button(
            info_frame,
            text="다음 단계",
            width=18,
            command=self.next_step,
        ).pack(
            pady=4
        )

        tk.Button(
            info_frame,
            text="자동 실행",
            width=18,
            command=self.start_auto_run,
        ).pack(
            pady=4
        )

        tk.Button(
            info_frame,
            text="자동 실행 중지",
            width=18,
            command=self.stop_auto_run,
        ).pack(
            pady=4
        )

        tk.Button(
            info_frame,
            text="다시 시작",
            width=18,
            command=self.reset_game,
        ).pack(
            pady=4
        )

        # 로그 영역
        self.log_text = tk.Text(
            self.root,
            height=17,
            width=100,
            font=("Consolas", 10),
        )

        self.log_text.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=10,
            pady=10,
        )

    def cell_display_text(self, cell):
        """
        지도 칸에 표시할 문자를 결정한다.
        """

        if cell == self.agent.position:
            arrows = {
                "East": "→",
                "South": "↓",
                "West": "←",
                "North": "↑",
            }

            return (
                "A"
                + arrows[self.agent.direction]
            )

        # 실제 지도 표시
        if self.show_real_world.get():
            symbols = []

            if (
                cell == self.env.gold
                and not self.env.gold_taken
            ):
                symbols.append("G")

            if (
                cell == self.env.wumpus
                and self.env.wumpus_alive
            ):
                symbols.append("W")

            if cell in self.env.pits:
                symbols.append("P")

            if symbols:
                return "".join(symbols)

        # 에이전트가 알고 있는 지도
        if cell in self.agent.visited:
            return "."

        if cell in self.agent.safe:
            return "S"

        if (
            cell in self.agent.possible_pit
            and cell in self.agent.possible_wumpus
        ):
            return "P?/W?"

        if cell in self.agent.possible_pit:
            return "P?"

        if cell in self.agent.possible_wumpus:
            return "W?"

        return "?"

    def cell_color(self, cell):
        """
        지도 칸의 배경색을 결정한다.
        """

        if cell == self.agent.position:
            return "#ffd966"

        if cell in self.agent.visited:
            return "#d9ead3"

        if cell in self.agent.safe:
            return "#cfe2f3"

        if (
            cell in self.agent.possible_pit
            or cell in self.agent.possible_wumpus
        ):
            return "#f4cccc"

        return "#f6f1df"

    def update_ui(self):
        """
        지도와 상태 정보를 갱신한다.
        """

        for cell, label in self.cells.items():
            label.config(
                text=self.cell_display_text(cell),
                bg=self.cell_color(cell),
            )

        status = (
            f"단계: {self.step_count}\n"
            f"현재 위치: {self.agent.position}\n"
            f"현재 방향: {self.agent.direction}\n"
            f"남은 화살: {self.agent.arrows}\n"
            f"Gold 보유 여부: {self.agent.has_gold}\n"
            f"Wumpus 생존 여부: {self.env.wumpus_alive}\n\n"
            f"방문한 칸: {sorted(self.agent.visited)}\n"
            f"안전한 칸: {sorted(self.agent.safe)}\n"
            f"Pit 가능 칸: {sorted(self.agent.possible_pit)}\n"
            f"Wumpus 가능 칸: "
            f"{sorted(self.agent.possible_wumpus)}"
        )

        self.status_label.config(
            text=status
        )

    def log(self, text):
        """
        로그 창에 메시지를 출력한다.
        """

        self.log_text.insert(
            tk.END,
            text + "\n",
        )

        self.log_text.see(
            tk.END
        )

    def next_step(self):
        """
        감지 → 추론 → 행동 과정을 한 단계 실행한다.
        """

        if self.game_over:
            return

        if self.step_count >= MAX_STEPS:
            self.finish_game(
                "임무 실패: 최대 단계 수를 초과했습니다."
            )
            return

        self.step_count += 1

        self.log(
            f"\n========== 단계 {self.step_count} =========="
        )

        # 감지
        percept = self.env.get_percept(
            self.agent
        )

        self.log(
            f"감지 정보: {percept}"
        )

        # 추론
        self.agent.update_knowledge(
            percept
        )

        self.log(
            "추론: 감지 정보를 바탕으로 "
            "지식 베이스를 갱신했습니다."
        )

        # 행동 선택
        action = self.agent.choose_action(
            percept
        )

        self.log(
            f"선택한 행동: {action}"
        )

        # 행동 실행
        result = self.env.execute_action(
            self.agent,
            action,
        )

        self.log(
            f"실행 결과: {result}"
        )

        self.update_ui()

        if self.env.game_success:
            self.finish_game(
                "임무 성공: Gold를 찾고 (1,1)로 돌아와 "
                "Climb을 실행했습니다!"
            )

        elif self.env.agent_dead:
            self.finish_game(
                "임무 실패: 에이전트가 사망했습니다."
            )

    def start_auto_run(self):
        """
        자동 실행을 시작한다.
        """

        if (
            self.game_over
            or self.auto_running
        ):
            return

        self.auto_running = True
        self.auto_run_once()

    def auto_run_once(self):
        """
        0.5초마다 한 단계씩 자동 실행한다.
        """

        if (
            not self.auto_running
            or self.game_over
        ):
            return

        self.next_step()

        if (
            self.auto_running
            and not self.game_over
        ):
            self.root.after(
                500,
                self.auto_run_once,
            )

    def stop_auto_run(self):
        """
        자동 실행을 중지한다.
        """

        self.auto_running = False

    def finish_game(self, message):
        """
        게임을 종료하고 결과를 표시한다.
        """

        self.game_over = True
        self.auto_running = False

        self.log(message)

        messagebox.showinfo(
            "결과",
            message,
        )

    def reset_game(self):
        """
        새로운 지도를 생성하고 게임을 다시 시작한다.
        """

        self.auto_running = False

        self.env = Environment()
        self.agent = Agent()

        self.step_count = 0
        self.game_over = False

        self.log_text.delete(
            "1.0",
            tk.END,
        )

        self.log(
            "게임을 다시 시작했습니다."
        )

        self.log(
            "목표: Gold를 찾고 (1,1)로 돌아와 "
            "Climb을 실행합니다."
        )

        self.update_ui()


# =====================================
# 프로그램 실행
# =====================================

def main():
    root = tk.Tk()

    WumpusWorldUI(root)

    root.mainloop()


if __name__ == "__main__":
    main()
```
