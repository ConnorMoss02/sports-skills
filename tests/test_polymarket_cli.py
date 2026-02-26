"""Tests for Polymarket CLI subprocess wrapper."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from sports_skills.polymarket._cli import (
    _CONFIG,
    _build_env,
    _find_binary,
    approve_check,
    cancel_all_orders,
    cli_search_markets,
    configure,
    create_order,
    ctf_split,
    get_balance,
    get_holders,
    get_leaderboard,
    get_positions,
    is_cli_available,
    run_cli,
)


class TestBinaryDiscovery:
    @patch("sports_skills.polymarket._cli.shutil.which", return_value="/usr/local/bin/polymarket")
    def test_find_binary_found(self, mock_which):
        assert _find_binary() == "/usr/local/bin/polymarket"

    @patch("sports_skills.polymarket._cli.shutil.which", return_value=None)
    def test_find_binary_not_found(self, mock_which):
        assert _find_binary() is None

    @patch("sports_skills.polymarket._cli.shutil.which", return_value="/usr/local/bin/polymarket")
    def test_is_cli_available_true(self, mock_which):
        assert is_cli_available() is True

    @patch("sports_skills.polymarket._cli.shutil.which", return_value=None)
    def test_is_cli_available_false(self, mock_which):
        assert is_cli_available() is False


class TestRunCli:
    @patch("sports_skills.polymarket._cli._find_binary", return_value=None)
    def test_binary_not_installed(self, mock_find):
        result = run_cli("markets", "list")
        assert result["status"] is False
        assert "not installed" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_successful_json_response(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"id": "1", "question": "Test?"}]),
            stderr="",
        )
        result = run_cli("markets", "list", "--limit", "1")
        assert result["status"] is True
        assert result["data"] == [{"id": "1", "question": "Test?"}]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_successful_dict_response(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"rank": 1, "pnl": 1234.56}),
            stderr="",
        )
        result = run_cli("data", "leaderboard")
        assert result["status"] is True
        assert result["data"]["rank"] == 1

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_nonzero_exit_code(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="connection failed")
        result = run_cli("markets", "list")
        assert result["status"] is False
        assert "connection failed" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_nonzero_exit_with_json_error(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({"error": "rate limited"}),
            stderr="",
        )
        result = run_cli("markets", "list")
        assert result["status"] is False
        assert "rate limited" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_invalid_json_output(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json{{{", stderr="")
        result = run_cli("markets", "list")
        assert result["status"] is False
        assert "invalid JSON" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_cli_json_error(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"error": "rate limited"}), stderr=""
        )
        result = run_cli("markets", "list")
        assert result["status"] is False
        assert "rate limited" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch(
        "sports_skills.polymarket._cli.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="polymarket", timeout=30),
    )
    def test_timeout(self, mock_run, mock_find):
        result = run_cli("data", "leaderboard")
        assert result["status"] is False
        assert "timed out" in result["message"]

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_empty_response(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = run_cli("markets", "list")
        assert result["status"] is True
        assert result["data"] is None

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_command_args_passed_correctly(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps([]), stderr=""
        )
        run_cli("markets", "list", "--limit", "5")
        mock_run.assert_called_once_with(
            ["/usr/local/bin/polymarket", "-o", "json", "markets", "list", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30,
            env=None,
        )


class TestCommandWrappers:
    """Test that wrapper functions pass correct args to run_cli."""

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_leaderboard_defaults(self, mock_run):
        mock_run.return_value = {"status": True, "data": [], "message": ""}
        get_leaderboard()
        mock_run.assert_called_once_with(
            "data", "leaderboard",
            "--period", "month",
            "--order-by", "pnl",
            "--limit", "20",
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_leaderboard_custom(self, mock_run):
        mock_run.return_value = {"status": True, "data": [], "message": ""}
        get_leaderboard(period="week", order_by="volume", limit=10)
        mock_run.assert_called_once_with(
            "data", "leaderboard",
            "--period", "week",
            "--order-by", "volume",
            "--limit", "10",
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_positions(self, mock_run):
        mock_run.return_value = {"status": True, "data": [], "message": ""}
        get_positions(address="0xabc")
        mock_run.assert_called_once_with("data", "positions", "0xabc")

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_cli_search_markets(self, mock_run):
        mock_run.return_value = {"status": True, "data": [], "message": ""}
        cli_search_markets(query="NBA", limit=5)
        mock_run.assert_called_once_with("markets", "search", "NBA", "--limit", "5")

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_holders(self, mock_run):
        mock_run.return_value = {"status": True, "data": [], "message": ""}
        get_holders(condition_id="0xcond123")
        mock_run.assert_called_once_with("data", "holders", "0xcond123")

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_create_order_defaults(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        create_order(token_id="0xtok", side="buy", price="0.55", size="10")
        mock_run.assert_called_once_with(
            "clob", "create-order",
            "--token", "0xtok",
            "--side", "buy",
            "--price", "0.55",
            "--size", "10",
            "--order-type", "GTC",
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_create_order_fok(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        create_order(token_id="0xtok", side="sell", price="0.80", size="5", order_type="FOK")
        mock_run.assert_called_once_with(
            "clob", "create-order",
            "--token", "0xtok",
            "--side", "sell",
            "--price", "0.80",
            "--size", "5",
            "--order-type", "FOK",
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_ctf_split(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        ctf_split(condition_id="0xcond", amount="100")
        mock_run.assert_called_once_with(
            "ctf", "split",
            "--condition", "0xcond",
            "--amount", "100",
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_cancel_all_orders(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        cancel_all_orders()
        mock_run.assert_called_once_with("clob", "cancel-all")

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_balance_default(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        get_balance()
        mock_run.assert_called_once_with(
            "clob", "balance", "--asset-type", "collateral"
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_get_balance_with_token(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        get_balance(asset_type="conditional", token_id="0xtok")
        mock_run.assert_called_once_with(
            "clob", "balance", "--asset-type", "conditional", "--token", "0xtok"
        )

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_approve_check_no_address(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        approve_check()
        mock_run.assert_called_once_with("approve", "check")

    @patch("sports_skills.polymarket._cli.run_cli")
    def test_approve_check_with_address(self, mock_run):
        mock_run.return_value = {"status": True, "data": {}, "message": ""}
        approve_check(address="0xaddr")
        mock_run.assert_called_once_with("approve", "check", "0xaddr")


class TestConfigure:
    """Test wallet configuration and env passthrough."""

    def setup_method(self):
        _CONFIG.clear()

    def teardown_method(self):
        _CONFIG.clear()

    def test_configure_private_key(self):
        result = configure(private_key="0xabc123")
        assert result["status"] is True
        assert _CONFIG["private_key"] == "0xabc123"

    def test_configure_signature_type(self):
        result = configure(signature_type="eoa")
        assert result["status"] is True
        assert _CONFIG["signature_type"] == "eoa"

    def test_configure_invalid_signature_type(self):
        result = configure(signature_type="invalid")
        assert result["status"] is False
        assert "signature_type" in result["message"]

    def test_configure_both(self):
        configure(private_key="0xkey", signature_type="proxy")
        assert _CONFIG["private_key"] == "0xkey"
        assert _CONFIG["signature_type"] == "proxy"

    def test_build_env_empty(self):
        assert _build_env() is None

    def test_build_env_with_key(self):
        _CONFIG["private_key"] = "0xtest"
        env = _build_env()
        assert env is not None
        assert env["POLYMARKET_PRIVATE_KEY"] == "0xtest"

    def test_build_env_with_signature_type(self):
        _CONFIG["private_key"] = "0xtest"
        _CONFIG["signature_type"] = "eoa"
        env = _build_env()
        assert env["POLYMARKET_PRIVATE_KEY"] == "0xtest"
        assert env["POLYMARKET_SIGNATURE_TYPE"] == "eoa"

    @patch("sports_skills.polymarket._cli._find_binary", return_value="/usr/local/bin/polymarket")
    @patch("sports_skills.polymarket._cli.subprocess.run")
    def test_run_cli_passes_env(self, mock_run, mock_find):
        _CONFIG["private_key"] = "0xsecret"
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"ok": True}), stderr=""
        )
        run_cli("clob", "balance")
        call_kwargs = mock_run.call_args
        env = call_kwargs.kwargs.get("env") or call_kwargs[1].get("env")
        assert env is not None
        assert env["POLYMARKET_PRIVATE_KEY"] == "0xsecret"
