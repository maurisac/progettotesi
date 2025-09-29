import json
import stats_generator
with open('bert_evaluation_20250307-034817.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
stats_generator.generate_confusion_matrix_chart(
    data['confusion_matrix'], 
    data['categories'], 
    'bert_confusion_matrix_manual.png'
)
print('Matrice di confusione generata: bert_confusion_matrix_manual.png')
