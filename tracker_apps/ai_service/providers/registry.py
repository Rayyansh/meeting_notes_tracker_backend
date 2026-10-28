from tracker.config import Configurations
from tracker.constants import Constants
from tracker_apps.ai_service.exceptions import ProviderConfigError
from tracker_apps.ai_service.providers.base import MeetingAnalysisProvider
from tracker_apps.ai_service.providers.mock import MockProvider


def get_provider() -> MeetingAnalysisProvider:
    """The one place a provider is chosen. A real provider plugs in here (see README)."""
    name = Configurations.ai_provider
    if name == Constants.ai_provider_mock:
        return MockProvider()
    raise ProviderConfigError(f"AI_PROVIDER '{name}' is not available")
