"""
Unit tests for isolation strategies.
"""

import os
import gc
import pytest
import warnings
from unittest.mock import Mock, patch, MagicMock

from plainbench.isolation.base import IsolationStrategy
from plainbench.isolation.minimal import MinimalIsolation
from plainbench.isolation.moderate import ModerateIsolation
from plainbench.isolation.maximum import MaximumIsolation
from plainbench.isolation.factory import (
    create_isolation_strategy,
    get_available_strategies,
    register_isolation_strategy,
)
from plainbench.isolation.system_utils import (
    get_platform,
    get_cpu_governor,
    is_turbo_boost_enabled,
    is_aslr_enabled,
    check_system_tuning,
)


class TestMinimalIsolation:
    """Test minimal isolation strategy."""

    def test_minimal_isolation_setup_teardown(self):
        """Test that minimal isolation setup and teardown do nothing."""
        isolation = MinimalIsolation()

        # Should not raise
        isolation.setup()
        isolation.teardown()

    def test_minimal_isolation_metadata(self):
        """Test minimal isolation metadata."""
        isolation = MinimalIsolation()
        metadata = isolation.get_metadata()

        assert metadata['strategy'] == 'MinimalIsolation'
        assert metadata['level'] == 'minimal'
        assert metadata['gc_control'] is True


class TestModerateIsolation:
    """Test moderate isolation strategy."""

    def test_moderate_isolation_init(self):
        """Test moderate isolation initialization."""
        isolation = ModerateIsolation()

        assert isolation.cpu_cores is None
        assert isolation.set_priority is True
        assert isolation.warn_tuning is True

    def test_moderate_isolation_init_with_params(self):
        """Test moderate isolation initialization with parameters."""
        isolation = ModerateIsolation(
            cpu_cores=[0, 1],
            set_priority=False,
            warn_tuning=False,
        )

        assert isolation.cpu_cores == [0, 1]
        assert isolation.set_priority is False
        assert isolation.warn_tuning is False

    def test_moderate_isolation_pythonhashseed(self):
        """Test PYTHONHASHSEED is set and restored."""
        # Save original
        original = os.environ.get('PYTHONHASHSEED')

        isolation = ModerateIsolation(warn_tuning=False)

        # Setup should set PYTHONHASHSEED=0
        isolation.setup()
        assert os.environ.get('PYTHONHASHSEED') == '0'

        # Teardown should restore original
        isolation.teardown()
        if original is not None:
            assert os.environ.get('PYTHONHASHSEED') == original
        else:
            assert 'PYTHONHASHSEED' not in os.environ

    def test_moderate_isolation_gc_control(self):
        """Test garbage collection is disabled and restored."""
        # Ensure GC is enabled
        gc.enable()
        assert gc.isenabled()

        isolation = ModerateIsolation(warn_tuning=False)

        # Setup should disable GC
        isolation.setup()
        assert not gc.isenabled()

        # Teardown should restore GC
        isolation.teardown()
        assert gc.isenabled()

    @pytest.mark.skipif(
        not hasattr(__import__('sys').modules.get('psutil'), 'Process'),
        reason="psutil not available"
    )
    def test_moderate_isolation_cpu_affinity_graceful_degradation(self):
        """Test CPU affinity fails gracefully without permissions."""
        isolation = ModerateIsolation(cpu_cores=[0], warn_tuning=False)

        # Should not raise even if CPU affinity fails
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()
            isolation.teardown()

    def test_moderate_isolation_metadata(self):
        """Test moderate isolation metadata."""
        isolation = ModerateIsolation(
            cpu_cores=[0, 1, 2, 3],
            warn_tuning=False
        )
        isolation.setup()

        try:
            metadata = isolation.get_metadata()

            assert metadata['strategy'] == 'ModerateIsolation'
            assert metadata['level'] == 'moderate'
            assert metadata['cpu_cores'] == [0, 1, 2, 3]
            assert metadata['pythonhashseed'] == '0'
            assert metadata['gc_disabled'] is True
            assert 'platform' in metadata
        finally:
            isolation.teardown()


class TestMaximumIsolation:
    """Test maximum isolation strategy."""

    def test_maximum_isolation_init(self):
        """Test maximum isolation initialization."""
        isolation = MaximumIsolation()

        assert isolation.minimal_env is True
        assert isolation.attempt_aslr_disable is False

    def test_maximum_isolation_init_with_params(self):
        """Test maximum isolation initialization with parameters."""
        isolation = MaximumIsolation(
            cpu_cores=[0, 1],
            minimal_env=False,
            attempt_aslr_disable=True,
            essential_env_vars={'MY_VAR'},
        )

        assert isolation.minimal_env is False
        assert isolation.attempt_aslr_disable is True
        assert 'MY_VAR' in isolation.essential_vars

    def test_maximum_isolation_environment_cleanup(self):
        """Test environment variable cleanup and restoration."""
        # Set some test environment variables
        os.environ['TEST_VAR_1'] = 'value1'
        os.environ['TEST_VAR_2'] = 'value2'
        original_env = dict(os.environ)

        isolation = MaximumIsolation(minimal_env=True)

        # Setup should clean environment
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        # Only essential vars should remain
        assert 'TEST_VAR_1' not in os.environ
        assert 'TEST_VAR_2' not in os.environ
        assert os.environ.get('PYTHONHASHSEED') == '0'

        # Teardown should restore environment
        isolation.teardown()
        assert os.environ.get('TEST_VAR_1') == 'value1'
        assert os.environ.get('TEST_VAR_2') == 'value2'

        # Cleanup
        del os.environ['TEST_VAR_1']
        del os.environ['TEST_VAR_2']

    def test_maximum_isolation_essential_vars_preserved(self):
        """Test essential environment variables are preserved."""
        # Set PATH
        original_path = os.environ.get('PATH', '/bin')
        os.environ['PATH'] = original_path

        isolation = MaximumIsolation(minimal_env=True)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        # PATH should be preserved
        assert os.environ.get('PATH') == original_path

        isolation.teardown()

    def test_maximum_isolation_metadata(self):
        """Test maximum isolation metadata."""
        isolation = MaximumIsolation(
            cpu_cores=[0, 1],
            minimal_env=True,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        try:
            metadata = isolation.get_metadata()

            assert metadata['strategy'] == 'MaximumIsolation'
            assert metadata['level'] == 'maximum'
            assert metadata['minimal_environment'] is True
            assert 'system_tuning' in metadata
            assert 'platform' in metadata['system_tuning']
        finally:
            isolation.teardown()

    def test_maximum_isolation_without_minimal_env(self):
        """Test maximum isolation without environment cleanup."""
        os.environ['TEST_VAR'] = 'test_value'

        isolation = MaximumIsolation(minimal_env=False)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        # Environment should not be cleaned
        assert os.environ.get('TEST_VAR') == 'test_value'

        isolation.teardown()

        # Cleanup
        del os.environ['TEST_VAR']


class TestIsolationFactory:
    """Test isolation strategy factory."""

    def test_create_minimal_isolation(self):
        """Test creating minimal isolation strategy."""
        strategy = create_isolation_strategy('minimal')
        assert isinstance(strategy, MinimalIsolation)

    def test_create_moderate_isolation(self):
        """Test creating moderate isolation strategy."""
        strategy = create_isolation_strategy('moderate')
        assert isinstance(strategy, ModerateIsolation)

    def test_create_maximum_isolation(self):
        """Test creating maximum isolation strategy."""
        strategy = create_isolation_strategy('maximum')
        assert isinstance(strategy, MaximumIsolation)

    def test_create_invalid_isolation(self):
        """Test creating invalid isolation strategy raises error."""
        with pytest.raises(ValueError, match="Unknown isolation level"):
            create_isolation_strategy('invalid')

    def test_get_available_strategies(self):
        """Test getting available strategies."""
        strategies = get_available_strategies()
        assert 'minimal' in strategies
        assert 'moderate' in strategies
        assert 'maximum' in strategies

    def test_register_custom_strategy(self):
        """Test registering custom isolation strategy."""
        class CustomIsolation(IsolationStrategy):
            def setup(self):
                pass

            def teardown(self):
                pass

        register_isolation_strategy('custom', CustomIsolation)

        # Should be able to create it
        strategy = create_isolation_strategy('custom')
        assert isinstance(strategy, CustomIsolation)

    def test_register_invalid_strategy(self):
        """Test registering invalid strategy raises error."""
        class NotAnIsolationStrategy:
            pass

        with pytest.raises(ValueError, match="must be a subclass"):
            register_isolation_strategy('invalid', NotAnIsolationStrategy)


class TestSystemUtils:
    """Test system utility functions."""

    def test_get_platform(self):
        """Test platform detection."""
        platform = get_platform()
        assert platform in ('linux', 'darwin', 'windows', 'unknown')

    def test_get_cpu_governor_returns_optional_str(self):
        """Test CPU governor detection returns valid type."""
        governor = get_cpu_governor()
        assert governor is None or isinstance(governor, str)

    def test_is_turbo_boost_enabled_returns_optional_bool(self):
        """Test turbo boost detection returns valid type."""
        turbo = is_turbo_boost_enabled()
        assert turbo is None or isinstance(turbo, bool)

    def test_is_aslr_enabled_returns_optional_bool(self):
        """Test ASLR detection returns valid type."""
        aslr = is_aslr_enabled()
        assert aslr is None or isinstance(aslr, bool)

    def test_check_system_tuning(self):
        """Test system tuning check."""
        info = check_system_tuning()

        assert 'platform' in info
        assert 'cpu_governor' in info
        assert 'turbo_boost_enabled' in info
        assert 'aslr_enabled' in info
        assert 'warnings' in info
        assert isinstance(info['warnings'], list)

    def test_check_system_tuning_on_linux(self):
        """Test system tuning check on Linux."""
        if get_platform() == 'linux':
            info = check_system_tuning()

            # On Linux, we should be able to detect some settings
            assert info['platform'] == 'linux'
            # cpu_governor might be None if not available, but should be present
            assert 'cpu_governor' in info


class TestIsolationIntegration:
    """Integration tests for isolation strategies."""

    def test_isolation_lifecycle_minimal(self):
        """Test full lifecycle of minimal isolation."""
        isolation = MinimalIsolation()

        isolation.setup()
        # Do some work
        result = sum(range(1000))
        assert result == 499500

        isolation.teardown()

    def test_isolation_lifecycle_moderate(self):
        """Test full lifecycle of moderate isolation."""
        isolation = ModerateIsolation(warn_tuning=False)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        # Do some work
        result = sum(range(1000))
        assert result == 499500

        isolation.teardown()

    def test_isolation_lifecycle_maximum(self):
        """Test full lifecycle of maximum isolation."""
        isolation = MaximumIsolation(minimal_env=True)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        # Do some work
        result = sum(range(1000))
        assert result == 499500

        isolation.teardown()

    def test_nested_isolation_fails_gracefully(self):
        """Test that nested isolation setup/teardown works correctly."""
        isolation1 = ModerateIsolation(warn_tuning=False)
        isolation2 = ModerateIsolation(warn_tuning=False)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            isolation1.setup()
            isolation2.setup()

            # Both should work
            isolation2.teardown()
            isolation1.teardown()

    def test_isolation_with_exception_handling(self):
        """Test isolation teardown happens even with exceptions."""
        isolation = ModerateIsolation(warn_tuning=False)

        gc_was_enabled = gc.isenabled()

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                isolation.setup()

            # Simulate exception
            raise RuntimeError("Test exception")

        except RuntimeError:
            pass
        finally:
            isolation.teardown()

        # GC should be restored
        assert gc.isenabled() == gc_was_enabled


class TestIsolationMetadata:
    """Test isolation metadata collection."""

    def test_minimal_metadata_structure(self):
        """Test minimal isolation metadata structure."""
        isolation = MinimalIsolation()
        metadata = isolation.get_metadata()

        assert 'strategy' in metadata
        assert 'level' in metadata
        assert metadata['level'] == 'minimal'

    def test_moderate_metadata_structure(self):
        """Test moderate isolation metadata structure."""
        isolation = ModerateIsolation(warn_tuning=False)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        try:
            metadata = isolation.get_metadata()

            assert 'strategy' in metadata
            assert 'level' in metadata
            assert 'cpu_pinning' in metadata
            assert 'cpu_cores' in metadata
            assert 'priority_adjustment' in metadata
            assert 'pythonhashseed' in metadata
            assert 'gc_disabled' in metadata
            assert 'platform' in metadata
        finally:
            isolation.teardown()

    def test_maximum_metadata_structure(self):
        """Test maximum isolation metadata structure."""
        isolation = MaximumIsolation(minimal_env=True)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            isolation.setup()

        try:
            metadata = isolation.get_metadata()

            assert 'strategy' in metadata
            assert 'level' in metadata
            assert 'minimal_environment' in metadata
            assert 'aslr_control_attempted' in metadata
            assert 'system_tuning' in metadata
            assert 'platform' in metadata['system_tuning']
        finally:
            isolation.teardown()
