"""
Mock data generation for Software Complexity Analysis Platform
"""

import random
from datetime import datetime, timedelta


def generate_complexity_data():
    """Generate mock complexity data for heatmap visualization"""
    file_names = [
        'api/routes.py', 'models/user.py', 'services/auth.py',
        'utils/helpers.py', 'controllers/main.py', 'db/migrations.py',
        'tests/unit_tests.py', 'config/settings.py', 'middleware/security.py',
        'views/dashboard.py', 'forms/validators.py', 'tasks/background.py',
        'api/serializers.py', 'models/product.py', 'services/payment.py'
    ]

    complexity_data = []
    for name in file_names:
        complexity_data.append({
            'name': name,
            'complexity': random.randint(10, 95),
            'lines': random.randint(50, 500)
        })

    return complexity_data


def generate_performance_metrics():
    """Generate mock performance metrics data"""

    time_complexity = [
        {'complexity': 'O(1)', 'count': random.randint(150, 200), 'description': 'Constant time'},
        {'complexity': 'O(log n)', 'count': random.randint(50, 80), 'description': 'Logarithmic'},
        {'complexity': 'O(n)', 'count': random.randint(80, 120), 'description': 'Linear'},
        {'complexity': 'O(n log n)', 'count': random.randint(30, 50), 'description': 'Linearithmic'},
        {'complexity': 'O(n²)', 'count': random.randint(10, 25), 'description': 'Quadratic'},
        {'complexity': 'O(2^n)', 'count': random.randint(1, 5), 'description': 'Exponential'}
    ]

    space_complexity = [
        {'complexity': 'O(1)', 'count': random.randint(200, 250), 'description': 'Constant space'},
        {'complexity': 'O(log n)', 'count': random.randint(40, 60), 'description': 'Logarithmic'},
        {'complexity': 'O(n)', 'count': random.randint(100, 150), 'description': 'Linear'},
        {'complexity': 'O(n²)', 'count': random.randint(5, 15), 'description': 'Quadratic'}
    ]

    return {
        'time_complexity': time_complexity,
        'space_complexity': space_complexity,
        'avg_execution_time': random.randint(5, 50),
        'memory_usage': round(random.uniform(50, 200), 2),
        'optimizable_functions': random.randint(15, 45)
    }


def generate_disk_space_data():
    """Generate mock disk space usage data"""

    file_types = [
        {'type': 'Python', 'size_mb': round(random.uniform(5, 25), 2), 'count': random.randint(100, 300)},
        {'type': 'JavaScript', 'size_mb': round(random.uniform(3, 15), 2), 'count': random.randint(50, 150)},
        {'type': 'JSON', 'size_mb': round(random.uniform(1, 5), 2), 'count': random.randint(20, 60)},
        {'type': 'CSS', 'size_mb': round(random.uniform(0.5, 3), 2), 'count': random.randint(10, 40)},
        {'type': 'HTML', 'size_mb': round(random.uniform(0.5, 2), 2), 'count': random.randint(15, 50)},
        {'type': 'Images', 'size_mb': round(random.uniform(10, 40), 2), 'count': random.randint(50, 200)},
        {'type': 'Other', 'size_mb': round(random.uniform(2, 10), 2), 'count': random.randint(30, 100)}
    ]

    largest_files = [
        {'file': 'static/images/banner_large.png', 'size_mb': round(random.uniform(5, 15), 2)},
        {'file': 'data/training_dataset.json', 'size_mb': round(random.uniform(8, 20), 2)},
        {'file': 'models/neural_network.py', 'size_mb': round(random.uniform(2, 8), 2)},
        {'file': 'dist/bundle.min.js', 'size_mb': round(random.uniform(3, 10), 2)},
        {'file': 'assets/video_intro.mp4', 'size_mb': round(random.uniform(15, 30), 2)}
    ]

    total_size = sum(ft['size_mb'] for ft in file_types)
    total_count = sum(ft['count'] for ft in file_types)

    return {
        'file_types': file_types,
        'largest_files': largest_files,
        'total_size_mb': round(total_size, 2),
        'file_count': total_count
    }


def generate_code_analysis_data():
    """Generate mock detailed code analysis data"""

    languages = [
        {'language': 'Python', 'percentage': random.randint(40, 60), 'lines': random.randint(10000, 30000)},
        {'language': 'JavaScript', 'percentage': random.randint(20, 35), 'lines': random.randint(5000, 15000)},
        {'language': 'TypeScript', 'percentage': random.randint(10, 20), 'lines': random.randint(3000, 8000)},
        {'language': 'CSS', 'percentage': random.randint(3, 8), 'lines': random.randint(1000, 3000)},
        {'language': 'HTML', 'percentage': random.randint(2, 5), 'lines': random.randint(500, 2000)}
    ]

    # Normalize percentages to 100%
    total_percentage = sum(lang['percentage'] for lang in languages)
    for lang in languages:
        lang['percentage'] = round((lang['percentage'] / total_percentage) * 100, 1)

    total_files = random.randint(150, 350)
    total_lines = sum(lang['lines'] for lang in languages)

    return {
        'total_files': total_files,
        'total_lines': total_lines,
        'total_functions': random.randint(500, 1500),
        'total_classes': random.randint(100, 300),
        'code_quality_score': random.randint(65, 95),
        'test_coverage': random.randint(60, 90),
        'documentation_coverage': random.randint(50, 85),
        'duplication_rate': round(random.uniform(2, 15), 1),
        'languages': languages,
        'issues': {
            'critical': random.randint(0, 5),
            'warnings': random.randint(10, 40),
            'code_smells': random.randint(20, 60),
            'security_hotspots': random.randint(2, 12)
        },
        'dependencies': {
            'total': random.randint(80, 200),
            'direct': random.randint(30, 60),
            'outdated': random.randint(5, 25),
            'vulnerable': random.randint(0, 8)
        }
    }


def generate_file_metrics():
    """Generate mock file-level metrics"""

    file_paths = [
        'src/api/routes/user_routes.py',
        'src/api/routes/product_routes.py',
        'src/models/user_model.py',
        'src/models/product_model.py',
        'src/services/authentication.py',
        'src/services/payment_processor.py',
        'src/utils/data_validator.py',
        'src/utils/string_helpers.py',
        'src/controllers/main_controller.py',
        'src/controllers/admin_controller.py',
        'src/middleware/auth_middleware.py',
        'src/middleware/rate_limiter.py',
        'src/database/connection.py',
        'src/database/migrations/001_initial.py',
        'src/config/app_settings.py',
        'src/config/database_config.py',
        'src/tests/test_authentication.py',
        'src/tests/test_user_routes.py',
        'src/views/dashboard_view.py',
        'src/views/reports_view.py'
    ]

    file_metrics = []

    for file_path in file_paths:
        complexity = random.randint(5, 95)
        maintainability = max(10, 100 - complexity + random.randint(-10, 10))

        file_metrics.append({
            'file': file_path,
            'lines': random.randint(50, 800),
            'complexity': complexity,
            'maintainability': min(100, maintainability),
            'functions': random.randint(3, 25),
            'classes': random.randint(0, 5)
        })

    return file_metrics


def generate_trend_data():
    """Generate mock trend data over time"""
    dates = []
    current_date = datetime.now()

    for i in range(30):
        dates.append(current_date - timedelta(days=29-i))

    trend_data = []
    base_complexity = random.randint(40, 60)

    for date in dates:
        # Add some variance to create realistic trends
        variance = random.randint(-5, 5)
        complexity = max(20, min(80, base_complexity + variance))
        base_complexity = complexity  # Carry over for next day

        trend_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'complexity': complexity,
            'code_quality': random.randint(60, 95),
            'test_coverage': random.randint(55, 90)
        })

    return trend_data
