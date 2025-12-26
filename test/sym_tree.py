import random
import time

# Параметры симуляции
GRID_WIDTH = 20  # Ширина грида (слева направо - движение жуков)
GRID_HEIGHT = 10  # Высота (ветки леса)
NUM_BUGS = 5  # Кол-во жуков
STEPS = 10  # Шаги симуляции

# Инициализация леса: каждая клетка - питательность (0-10)
forest = [[random.randint(0, 10) for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Жуки: [позиция_x, позиция_y, размер, энергия]
# Размер влияет на скорость поедания и подвижность
bugs = []
for i in range(NUM_BUGS):
    size = random.uniform(0.5, 2.0)  # Стартовый размер (маленькие/большие)
    bugs.append([0, random.randint(0, GRID_HEIGHT - 1), size, 10 * size])  # Энергия пропорциональна размеру


def print_grid():
    for y in range(GRID_HEIGHT):
        row = []
        for x in range(GRID_WIDTH):
            cell = forest[y][x]
            bug_here = any(b[0] == x and b[1] == y for b in bugs)
            if bug_here:
                row.append('B')
            elif cell > 0:
                row.append(str(cell))
            else:
                row.append('.')
        print(' '.join(row))
    print("\n")


def simulate_step():
    for bug in bugs[:]:  # Копируем список, чтобы удалять мертвых
        x, y, size, energy = bug

        if energy <= 0:
            bugs.remove(bug)
            continue

        # Поедание: скорость = size, потребление энергии = size * 0.5
        if x < GRID_WIDTH and forest[y][x] > 0:
            eat_amount = min(forest[y][x], size * 2)  # Большие едят быстрее
            forest[y][x] -= eat_amount
            energy += eat_amount
            energy -= size * 0.5  # Стоимость поедания

        # Движение направо, энергия на шаг -1
        if x < GRID_WIDTH - 1:
            x += 1
            energy -= 1

        # Подвижность: шанс сменить ветку (y) на лучшую, пропорционально size
        if random.random() < size / 2:  # Max 1.0 шанс для size=2
            best_y = y
            best_nutr = forest[best_y][x] if x < GRID_WIDTH else 0
            for dy in [-1, 1]:  # Проверяем соседние ветки
                ny = y + dy
                if 0 <= ny < GRID_HEIGHT:
                    nutr = forest[ny][x] if x < GRID_WIDTH else 0
                    if nutr > best_nutr:
                        best_y = ny
                        best_nutr = nutr
            y = best_y
            energy -= 0.5  # Стоимость смены

        # Рост: размер растет от энергии
        if energy > 10 * size:
            size += 0.1
            energy -= 5

        bug[:] = [x, y, size, energy]

    # Регенерация леса: слева направо, но рост справа налево (добавляем в правых колонках)
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH - 1, -1, -1):  # С права налево
            if random.random() < 0.1:
                forest[y][x] += random.randint(1, 3)
                if forest[y][x] > 10:
                    forest[y][x] = 10

def main():
    print("Initial grid:")
    print_grid()

    for step in range(STEPS):
        print(f"Step {step + 1}:")
        simulate_step()
        print_grid()
        print("Bugs status:")
        for i, bug in enumerate(bugs):
            print(f"Bug {i}: Pos ({bug[0]},{bug[1]}), Size {bug[2]:.2f}, Energy {bug[3]:.2f}")
        print("\n")
        time.sleep(0.5)  # Для динамики, но в REPL игнорируется

if __name__ == '__main__':
    main()