"""Детальная инспекция найденных датасетов."""
import json
from pathlib import Path
from datasets import load_dataset
from kaggle.api.kaggle_api_extended import KaggleApi


def inspect_huggingface_dataset(dataset_id: str):
    """Инспектирует HuggingFace датасет."""
    print(f"\n{'='*70}")
    print(f"INSPECTING: {dataset_id}")
    print('='*70)
    
    try:
        # Загружаем датасет
        ds = load_dataset(dataset_id, split='train', trust_remote_code=True)
        
        print(f"Size: {len(ds)} examples")
        print(f"Features: {list(ds.features.keys())}")
        
        # Показываем примеры
        print("\nSample examples:")
        for i, example in enumerate(ds[:3]):
            print(f"\nExample {i+1}:")
            for key, value in example.items():
                value_str = str(value)[:200] if value else "None"
                print(f"  {key}: {value_str}")
        
        # Проверяем наличие полей для MCQ
        has_question = any('question' in str(k).lower() for k in ds.features.keys())
        has_answer = any('answer' in str(k).lower() for k in ds.features.keys())
        
        print(f"\nMCQ Fields:")
        print(f"  Question field: {'YES' if has_question else 'NO'}")
        print(f"  Answer field: {'YES' if has_answer else 'NO'}")
        
        return {
            'id': dataset_id,
            'size': len(ds),
            'features': list(ds.features.keys()),
            'has_mcq': has_question and has_answer
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def inspect_kaggle_dataset(dataset_ref: str):
    """Инспектирует Kaggle датасет."""
    print(f"\n{'='*70}")
    print(f"INSPECTING: {dataset_ref}")
    print('='*70)
    
    api = KaggleApi()
    api.authenticate()
    
    try:
        # Получаем метаданные
        metadata = api.dataset_metadata_view(dataset_ref)
        print(f"Title: {metadata.title if hasattr(metadata, 'title') else 'N/A'}")
        print(f"License: {metadata.licenseName if hasattr(metadata, 'licenseName') else 'N/A'}")
        print(f"Description: {metadata.subtitle[:200] if hasattr(metadata, 'subtitle') else 'N/A'}...")
        
        # Скачиваем
        download_path = Path(f"data/inspection/{dataset_ref.replace('/', '_')}")
        download_path.mkdir(parents=True, exist_ok=True)
        
        api.dataset_download_files(dataset_ref, path=str(download_path), unzip=True)
        
        # Показываем файлы
        files = list(download_path.glob('*'))
        print(f"\nFiles: {[f.name for f in files]}")
        
        return {
            'ref': dataset_ref,
            'files': [f.name for f in files],
            'path': str(download_path)
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Основная функция."""
    
    # Приоритетные HuggingFace датасеты
    hf_priority = [
        "Romyx/ru_QA_school_history",
        "AIR-Bench/qa_science_ru",
        "AIR-Bench/qa_wiki_ru",
        "hivaze/ru-AAQG-QA-QG",
    ]
    
    # Приоритетные Kaggle датасеты
    kaggle_priority = [
        "valentinbiryukov/rubq-20",
        "valentinbiryukov/rubq-10",
        "d0rj3228/russian-literature",
        "goldian/writers",
    ]
    
    print("="*70)
    print("DETAILED DATASET INSPECTION")
    print("="*70)
    
    # Инспектируем HuggingFace
    print("\n\n### HUGGINGFACE DATASETS ###")
    hf_results = []
    for ds_id in hf_priority:
        result = inspect_huggingface_dataset(ds_id)
        if result:
            hf_results.append(result)
    
    # Инспектируем Kaggle
    print("\n\n### KAGGLE DATASETS ###")
    kaggle_results = []
    for ds_ref in kaggle_priority:
        result = inspect_kaggle_dataset(ds_ref)
        if result:
            kaggle_results.append(result)
    
    # Сводка
    print("\n" + "="*70)
    print("INSPECTION SUMMARY")
    print("="*70)
    
    print(f"\nHuggingFace datasets inspected: {len(hf_results)}")
    for r in hf_results:
        mcq_status = "[OK]" if r['has_mcq'] else "[NO MCQ]"
        print(f"  {mcq_status} {r['id']}: {r['size']} examples")
    
    print(f"\nKaggle datasets inspected: {len(kaggle_results)}")
    for r in kaggle_results:
        print(f"  [OK] {r['ref']}: {len(r['files'])} files")


if __name__ == "__main__":
    main()
