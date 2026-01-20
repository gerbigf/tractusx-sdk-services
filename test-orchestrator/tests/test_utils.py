"""Test for utility methods
"""
import pytest
from unittest.mock import MagicMock, patch

from test_orchestrator.base_utils import submodel_validation
from test_orchestrator.errors import HTTPError, Error


@pytest.mark.asyncio
async def test_no_submodel_descriptors_key():
    """Should raise error when 'submodelDescriptors' key is missing."""
    with pytest.raises(HTTPError) as exc:
        await submodel_validation("BPNL123", {}, "semID")

    assert exc.value.error_code == Error.NO_SHELLS_FOUND


@pytest.mark.asyncio
async def test_empty_submodel_descriptors():
    """Should raise error when list is empty."""
    data = {"submodelDescriptors": []}

    with pytest.raises(HTTPError) as exc:
        await submodel_validation("BPNL123", data, "semID")

    assert exc.value.error_code == Error.NO_SHELLS_FOUND


@pytest.mark.asyncio
@patch("test_orchestrator.base_utils.schema_finder")
@patch("test_orchestrator.base_utils.json_validator")
async def test_schema_validation_error(json_validator_mock, schema_finder_mock):
    """Should throw UNPROCESSABLE_ENTITY when shell descriptor schema is nok."""
    schema_finder_mock.return_value = {"dummy": True}
    json_validator_mock.return_value = {"status": "nok"}

    data = {
        "submodelDescriptors": [
            {"semanticId": {"keys": [{"value": "semID"}]}}
        ]
    }

    with pytest.raises(HTTPError) as exc:
        await submodel_validation("BPNL", data, "semID")

    assert exc.value.error_code == Error.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("test_orchestrator.base_utils.schema_finder")
@patch("test_orchestrator.base_utils.json_validator")
async def test_semantic_id_not_found(json_validator_mock, schema_finder_mock):
    """Should raise SUBMODEL_DESCRIPTOR_NOT_FOUND when semanticId does not match."""
    schema_finder_mock.return_value = {}
    json_validator_mock.return_value = {"status": "ok"}

    data = {
        "submodelDescriptors": [
            {"semanticId": {"keys": [{"value": "different"}]}}
        ]
    }

    with pytest.raises(HTTPError) as exc:
        await submodel_validation("BPNL", data, "semID")

    assert exc.value.error_code == Error.SUBMODEL_DESCRIPTOR_NOT_FOUND


@pytest.mark.asyncio
@patch("test_orchestrator.base_utils.schema_finder")
@patch("test_orchestrator.base_utils.json_validator")
@patch("test_orchestrator.base_utils.fetch_submodel_info")
@patch("test_orchestrator.base_utils.get_dataplane_access")
@patch("test_orchestrator.base_utils.httpx.get")
async def test_http_error_on_submodel_download(
    httpx_get_mock,
    get_dataplane_access_mock,
    fetch_submodel_info_mock,
    json_validator_mock,
    schema_finder_mock,
):
    """Should raise error if submodel href request → non-200."""
    schema_finder_mock.return_value = {}
    json_validator_mock.return_value = {"status": "ok"}

    data = {
        "submodelDescriptors": [
            {"semanticId": {"keys": [{"value": "semID"}]}}
        ]
    }

    fetch_submodel_info_mock.return_value = {
        "href": "http://test.com/submodel",
        "subm_counterparty": "BPNL",
        "subm_operandleft": "opL",
        "subm_operandright": "opR"
    }

    get_dataplane_access_mock.return_value = ("url", "api-key", None)

    httpx_get_mock.return_value = MagicMock(status_code=404)

    with pytest.raises(HTTPError) as exc:
        await submodel_validation("BPNL", data, "semID")

    assert exc.value.error_code == Error.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("test_orchestrator.base_utils.schema_finder")
@patch("test_orchestrator.base_utils.json_validator")
@patch("test_orchestrator.base_utils.fetch_submodel_info")
@patch("test_orchestrator.base_utils.get_dataplane_access")
@patch("test_orchestrator.base_utils.httpx.get")
@patch("test_orchestrator.base_utils.submodel_schema_finder")
async def test_successful_validation(
    schema_finder_submodel_mock,
    httpx_get_mock,
    get_dataplane_access_mock,
    fetch_submodel_info_mock,
    json_validator_mock,
    schema_finder_mock,
):
    """Full happy-path test — all mocks return OK."""

    schema_finder_mock.return_value = {"shell": True}
    json_validator_mock.side_effect = [
        {"status": "ok"},  # shell descriptor validation
        {"status": "ok"}   # submodel validation
    ]

    data = {
        "submodelDescriptors": [
            {"semanticId": {"keys": [{"value": "semID"}]}}
        ]
    }

    fetch_submodel_info_mock.return_value = {
        "href": "http://test.com/submodel",
        "subm_counterparty": "BPNL",
        "subm_operandleft": "opL",
        "subm_operandright": "opR"
    }

    get_dataplane_access_mock.return_value = ("url", "api-key", None)

    httpx_get_mock.return_value = MagicMock(
        status_code=200,
        json=lambda: {"submodel": "data"}
    )

    schema_finder_submodel_mock.return_value = {"schema": {"id": "schema"}}
    result = await submodel_validation("BPNL", data, "semID")

    assert result == {"status": "ok"}
