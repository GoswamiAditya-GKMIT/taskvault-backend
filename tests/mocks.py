import pytest
from django.conf import settings

@pytest.fixture
def mock_celery_task(mocker):
    """
    Mocks the `.delay()` method of a Celery task.
    """
    def _mock_celery_task(task_path):
        return mocker.patch(f"{task_path}.delay")
    return _mock_celery_task

@pytest.fixture
def mock_send_mail(mocker):
    """ Mocks Django's send_mail helper. """
    return mocker.patch('django.core.mail.send_mail')

@pytest.fixture
def mock_redis_cache(mocker):
    """ Mocks Django's default caching mechanism. """
    return mocker.patch('django.core.cache.cache')

@pytest.fixture
def mock_razorpay_client(mocker):
    """
    Mocks the Razorpay python client. 
    It patches the class and the instance in subscriptions.services.
    """
    mock_class = mocker.patch('razorpay.Client')
    mocker.patch('subscriptions.services.client', mock_class.return_value)
    return mock_class
