"""
Систематический поиск русскоязычных датасетов для викторины.
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def search_huggingface_datasets():
    """Поиск датасетов на HuggingFace."""
    try:
        from huggingface_hub import HfApi, list_datasets
        
        api = HfApi()
        
        # Поисковые запросы
        keywords = [
            "russian quiz", "russian trivia", "ru qa", 
            "russian multiple choice", "russian question answering",
            "викторина", "русский язык вопросы"
        ]
        
        all_results = []
        
        print("Searching HuggingFace...")
        for keyword in keywords:
            try:
                datasets = list_datasets(
                    search=keyword,
                    limit=50
                )
                
                for ds in datasets:
                    try:
                        info = api.dataset_info(ds.id)
                        card = info.cardData or {}
                        
                        result = {
                            "platform": "HuggingFace",
                            "id": ds.id,
                            "name": ds.id.split('/')[-1],
                            "url": f"https://huggingface.co/datasets/{ds.id}",
                            "license": card.get('license', 'Unknown'),
                            "language": card.get('language', []),
                            "tags": card.get('tags', []),
                            "downloads": ds.downloads if hasattr(ds, 'downloads') else 0,
                            "search_keyword": keyword
                        }
                        
                        # Фильтруем по языку
                        if isinstance(result['language'], list):
                            langs = result['language']
                        else:
                            langs = [result['language']] if result['language'] else []
                        
                        if 'ru' in langs or 'russian' in langs or 'multilingual' in langs:
                            all_results.append(result)
                            print(f"  Found: {ds.id}")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Error searching '{keyword}': {e}")
                continue
        
        # Убираем дубликаты
        seen = set()
        unique = []
        for r in all_results:
            if r['id'] not in seen:
                seen.add(r['id'])
                unique.append(r)
        
        return unique
        
    except Exception as e:
        print(f"HuggingFace search error: {e}")
        return []


def search_kaggle_datasets():
    """Поиск датасетов на Kaggle."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        api.authenticate()
        
        # Поисковые запросы
        keywords = [
            "russian trivia", "викторина", "ru quiz", "russian quiz",
            "russian multiple choice", "ru MCQ", "russian questions",
            "russian history", "russian literature", "russian geography"
        ]
        
        all_results = []
        
        print("\nSearching Kaggle...")
        for keyword in keywords:
            try:
                datasets = api.dataset_list(search=keyword, sort_by="votes")
                
                for ds in datasets[:20]:  # Ограничиваем количество
                    try:
                        # Получаем метаданные
                        result = {
                            "platform": "Kaggle",
                            "id": ds.ref,
                            "name": ds.title if hasattr(ds, 'title') else ds.ref.split('/')[-1],
                            "url": f"https://www.kaggle.com/datasets/{ds.ref}",
                            "license": ds.license if hasattr(ds, 'license') else 'Unknown',
                            "size": ds.size if hasattr(ds, 'size') else None,
                            "votes": ds.votes if hasattr(ds, 'votes') else 0,
                            "downloads": ds.downloadCount if hasattr(ds, 'downloadCount') else 0,
                            "search_keyword": keyword
                        }
                        
                        all_results.append(result)
                        print(f"  Found: {ds.ref}")
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Error searching '{keyword}': {e}")
                continue
        
        # Убираем дубликаты
        seen = set()
        unique = []
        for r in all_results:
            if r['id'] not in seen:
                seen.add(r['id'])
                unique.append(r)
        
        return unique
        
    except Exception as e:
        print(f"Kaggle search error: {e}")
        return []


def analyze_license(license_str):
    """Анализирует лицензию на коммерческую пригодность."""
    if not license_str:
        return "Unknown", "⚠️"
    
    license_upper = str(license_str).upper()
    
    # Разрешенные лицензии
    commercial_ok = ["CC0", "CC BY", "CC BY-SA", "PUBLIC DOMAIN", "APACHE 2.0", "MIT", "BSD"]
    for ok in commercial_ok:
        if ok in license_upper:
            return "Commercial OK", "✅"
    
    # Запрещенные лицензии
    if "NC" in license_upper or "NON-COMMERCIAL" in license_upper:
        return "Non-Commercial", "❌"
    
    if "ACADEMIC" in license_upper or "RESEARCH" in license_upper:
        return "Research Only", "❌"
    
    return "Unknown", "⚠️"


def main():
    """Основная функция поиска."""
    print("="*70)
    print("RUSSIAN QUIZ DATASETS SEARCH")
    print("="*70)
    print(f"Start time: {datetime.now()}")
    
    # Поиск на обеих платформах
    hf_results = search_huggingface_datasets()
    kaggle_results = search_kaggle_datasets()
    
    all_results = hf_results + kaggle_results
    
    print(f"\n{'='*70}")
    print(f"TOTAL FOUND: {len(all_results)} datasets")
    print(f"{'='*70}")
    
    if not all_results:
        print("No datasets found!")
        return
    
    # Создаем DataFrame для анализа
    df = pd.DataFrame(all_results)
    
    # Добавляем анализ лицензий
    license_analysis = df['license'].apply(analyze_license)
    df['license_status'] = [x[0] for x in license_analysis]
    df['license_emoji'] = [x[1] for x in license_analysis]
    
    # Статистика по платформам
    print("\nBy Platform:")
    print(df['platform'].value_counts())
    
    # Статистика по лицензиям
    print("\nBy License Status:")
    print(df['license_status'].value_counts())
    
    # Фильтруем коммерчески пригодные
    commercial_df = df[df['license_status'] == 'Commercial OK']
    print(f"\n[OK] Commercially usable: {len(commercial_df)}")
    
    # Сохраняем результаты
    output_dir = Path("data/search_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Все результаты
    df.to_json(output_dir / "all_datasets.json", orient="records", indent=2, force_ascii=False)
    df.to_csv(output_dir / "all_datasets.csv", index=False, encoding="utf-8-sig")
    
    # Только коммерчески пригодные
    commercial_df.to_json(output_dir / "commercial_datasets.json", orient="records", indent=2, force_ascii=False)
    commercial_df.to_csv(output_dir / "commercial_datasets.csv", index=False, encoding="utf-8-sig")
    
    print(f"\nSaved to:")
    print(f"  - {output_dir}/all_datasets.json")
    print(f"  - {output_dir}/commercial_datasets.csv")
    
    # Показываем топ-10 по скачиваниям
    if 'downloads' in df.columns:
        print("\n" + "="*70)
        print("TOP 10 DATASETS BY DOWNLOADS:")
        print("="*70)
        top10 = df.nlargest(10, 'downloads')[['platform', 'name', 'license_emoji', 'downloads', 'url']]
        for idx, row in top10.iterrows():
            print(f"{row['license_emoji']} {row['name'][:40]:<40} | {row['downloads']:,} downloads")
            print(f"   {row['url']}")
    
    print(f"\nEnd time: {datetime.now()}")


if __name__ == "__main__":
    main()
