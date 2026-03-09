#!/usr/bin/env python3
"""Проверка результата исправления вопросов."""

import sqlite3
import json

conn = sqlite3.connect('quiz_bot.db')
c = conn.cursor()

print('=== ПРОВЕРКА РЕЗУЛЬТАТА ===\n')

# Примеры вопросов
c.execute('SELECT text, correct_answer, wrong_answers, category FROM questions LIMIT 5')
for i, row in enumerate(c.fetchall(), 1):
    print(f'Вопрос {i}: {row[0][:60]}...')
    print(f'  Категория: {row[3]}')
    print(f'  Правильный: {row[1]}')
    try:
        wrong = json.loads(row[2])
        print(f'  Неправильные: {wrong}')
    except:
        print(f'  Неправильные: {row[2]}')
    print()

# Проверка нет ли заглушек
c.execute("SELECT COUNT(*) FROM questions WHERE wrong_answers LIKE '%Вариант 1%'")
stub_count = c.fetchone()[0]
print(f'Осталось заглушек "Вариант 1": {stub_count}')

# Статистика по категориям
print('\n=== КАТЕГОРИИ ===')
c.execute('SELECT category, COUNT(*) FROM questions GROUP BY category ORDER BY COUNT(*) DESC')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Статистика по сложности
print('\n=== СЛОЖНОСТЬ ===')
c.execute('SELECT difficulty, COUNT(*) FROM questions GROUP BY difficulty ORDER BY COUNT(*) DESC')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()
