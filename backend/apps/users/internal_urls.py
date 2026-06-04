from django.urls import path
from .internal_views import create_learning_path, create_chapter_learning_path, get_learning_path_progress, get_pretest_results, update_item_status, save_post_test_result

urlpatterns = [
    path('create-learning-path/', create_learning_path, name='internal-create-learning-path'),
    path('create-chapter-learning-path/', create_chapter_learning_path, name='internal-create-chapter-learning-path'),
    path('learning-path/progress/', get_learning_path_progress, name='internal-lp-progress'),
    path('learning-path/pre-test-results/', get_pretest_results, name='internal-pretest-results'),
    path('learning-path/item/complete/', update_item_status, name='internal-lp-item-complete'),
    path('save-post-test-result/', save_post_test_result, name='internal-save-post-test-result'),
]
