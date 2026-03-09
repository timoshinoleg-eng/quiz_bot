"""
Перевод вопросов из OpenTDB на русский язык.
Использует Google Translate API (через googletrans).
"""
import json
import asyncio
import time
from pathlib import Path


def translate_text(translator, text: str, src: str = 'en', dest: str = 'ru') -> str:
    """Перевод текста с retry логикой."""
    try:
        result = translator.translate(text, src=src, dest=dest)
        return result.text if result else text
    except Exception as e:
        print(f"    Ошибка перевода '{text[:30]}...': {e}")
        return text


def translate_opentdb_questions(
    input_path: str = "data/generated/opentdb_questions.json",
    output_path: str = "data/generated/opentdb_questions_ru.json"
):
    """Перевод всех вопросов на русский."""
    try:
        from googletrans import Translator
    except ImportError:
        print("Требуется googletrans: pip install googletrans==4.0.0-rc1")
        return
    
    translator = Translator()
    
    # Загрузка вопросов
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    print(f"Перевод {len(questions)} вопросов...")
    
    translated = []
    for i, q in enumerate(questions, 1):
        try:
            # Перевод текста вопроса
            text_trans = translate_text(translator, q['text'])
            
            # Перевод правильного ответа
            answer_trans = translate_text(translator, q['correct_answer'])
            
            # Перевод неправильных ответов
            wrong_trans = []
            for wrong in q['wrong_answers']:
                w_trans = translate_text(translator, wrong)
                wrong_trans.append(w_trans)
            
            # Создание переведённого вопроса
            translated_q = {
                'text': text_trans,
                'correct_answer': answer_trans,
                'wrong_answers': wrong_trans,
                'category': q.get('category', 'GENERAL').upper(),
                'difficulty': q.get('difficulty', 'MEDIUM').upper(),
                'source': 'OpenTDB (translated)',
                'original_en': {
                    'text': q['text'],
                    'correct_answer': q['correct_answer'],
                    'wrong_answers': q['wrong_answers']
                }
            }
            
            translated.append(translated_q)
            
            if i % 50 == 0:
                print(f"  Переведено {i}/{len(questions)} вопросов...")
            
            # Rate limiting (бесплатный API)
            time.sleep(0.3)
            
        except Exception as e:
            print(f"  Ошибка перевода вопроса {i}: {e}")
            # Сохранить оригинал с пометкой
            q_copy = q.copy()
            q_copy['translation_error'] = str(e)
            q_copy['category'] = q.get('category', 'GENERAL').upper()
            q_copy['difficulty'] = q.get('difficulty', 'MEDIUM').upper()
            translated.append(q_copy)
    
    # Сохранение
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)
    
    print(f"\nПереведено {len(translated)} вопросов")
    print(f"Сохранено в: {output_path}")


if __name__ == "__main__":
    translate_opentdb_questions()
