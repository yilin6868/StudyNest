from app.services.phrases import PHRASES, local_reply, scene_reply


def test_empty_input_returns_greet():
    assert local_reply("") in PHRASES["greet"]


def test_tired_route():
    assert local_reply("我好累啊，想休息") in PHRASES["tired"]


def test_encourage_route():
    assert local_reply("给我点鼓励") in PHRASES["encourage"]


def test_method_route():
    assert local_reply("怎么背单词记不住") in PHRASES["method"]


def test_celebrate_route():
    assert local_reply("我完成了一个番茄钟") in PHRASES["celebrate"]


def test_greet_route():
    assert local_reply("你好呀") in PHRASES["greet"]


def test_goal_route():
    assert "目标" in local_reply("今天我要学英语")


def test_fallback_route():
    assert local_reply("随便说点什么xyz") in PHRASES["fallback"]


def test_scene_reply_all_valid_scenes():
    for scene in ["greet", "start", "encourage", "celebrate", "break", "breakOver", "tired", "idle"]:
        assert scene_reply(scene) in PHRASES[scene]


def test_scene_reply_unknown_falls_back():
    assert scene_reply("nonexistent") in PHRASES["fallback"]
