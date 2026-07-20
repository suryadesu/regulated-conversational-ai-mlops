"""Unit tests for the graceful-drain state machine."""

import asyncio

import pytest

from gateway.draining import DrainState


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_fresh_state_not_draining() -> None:
    assert DrainState().is_draining is False


def test_begin_drain_flips_flag() -> None:
    state = DrainState()
    state.begin_drain()
    assert state.is_draining is True


@pytest.mark.anyio
async def test_wait_for_drain_empty_returns_true_immediately() -> None:
    assert await DrainState().wait_for_drain(0.1) is True


@pytest.mark.anyio
async def test_wait_blocks_while_request_open_then_releases() -> None:
    state = DrainState()
    release = asyncio.Event()
    entered = asyncio.Event()

    async def held_request() -> None:
        async with state.track_request():
            entered.set()
            await release.wait()

    task = asyncio.create_task(held_request())
    await asyncio.wait_for(entered.wait(), timeout=2)
    assert await state.wait_for_drain(0.05) is False  # still in flight

    release.set()
    await task
    assert await state.wait_for_drain(0.5) is True


@pytest.mark.anyio
async def test_counter_decrements_even_on_exception() -> None:
    state = DrainState()
    with pytest.raises(RuntimeError):
        async with state.track_request():
            raise RuntimeError("boom")
    assert await state.wait_for_drain(0.1) is True
