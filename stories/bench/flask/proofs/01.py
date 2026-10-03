import os

# DEBUG is read from the environment at construction time; the trace run had it unset.
os.environ.pop("FLASK_DEBUG", None)

from flask import Flask
from flask.config import Config
from flask.helpers import get_root_path
from flask.sansio.scaffold import find_package

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"


# --- what Scaffold/App derived from the single input string -------------------
assert app.import_name == __name__
assert os.path.isabs(app.root_path)
assert app.root_path == get_root_path(app.import_name)

prefix, package_path = find_package(app.import_name)
expected_instance = (
    os.path.join(package_path, "instance")
    if prefix is None
    else os.path.join(prefix, "var", f"{app.name}-instance")
)
assert app.instance_path == expected_instance
assert os.path.basename(app.instance_path).endswith("instance")

# --- make_config: 29 defaults, with DEBUG overwritten by get_debug_flag() -----
assert isinstance(app.config, Config)
assert len(app.config) == 29
assert Flask.default_config["DEBUG"] is None  # declared default
assert app.config["DEBUG"] is False  # effective default, from the environment
assert app.debug is False
assert app.config["SECRET_KEY"] is None
assert app.secret_key is None
assert app.config["TESTING"] is False
assert app.config["PROPAGATE_EXCEPTIONS"] is None
assert app.config["TRUSTED_HOSTS"] is None
assert app.config["SERVER_NAME"] is None
assert app.config["PREFERRED_URL_SCHEME"] == "http"
assert app.config["APPLICATION_ROOT"] == "/"
assert app.config["PROVIDE_AUTOMATIC_OPTIONS"] is True

# --- the static route is added unconditionally, path derived from the folder --
assert app.has_static_folder is True
assert app.static_folder == os.path.join(app.root_path, "static")
assert app.static_url_path == "/static"

# --- the two rules in the map ------------------------------------------------
rules = {r.rule: r for r in app.url_map.iter_rules()}
assert set(rules) == {"/static/<path:filename>", "/"}
assert rules["/static/<path:filename>"].endpoint == "static"
assert rules["/"].endpoint == "hello"  # from _endpoint_from_view_func
assert rules["/"].methods == {"GET", "HEAD", "OPTIONS"}
assert rules["/"].provide_automatic_options is True
assert app.view_functions["hello"] is hello
assert "static" in app.view_functions

# --- no hooks registered; the setup lock is not engaged yet -------------------
assert app.before_request_funcs == {}
assert app.after_request_funcs == {}
assert app.teardown_request_funcs == {}
assert app.teardown_appcontext_funcs == []
assert app._got_first_request is False
assert app._check_setup_finished("route") is None

# --- the Click group is named after the app ----------------------------------
assert app.cli.name == app.name

print("chapter 1 ok")
