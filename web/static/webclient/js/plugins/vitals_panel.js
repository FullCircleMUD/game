/*
 * FCM Vitals Panel Plugin
 *
 * Listens for "vitals_update" OOB events and renders HP/MP/MV
 * progress bars in the #side-panel. Only active on the split client.
 *
 * Registered as a proper Evennia plugin via plugin_handler so that
 * custom OOB events (routed through onUnknownCmd) are handled correctly.
 */
let vitals_panel_plugin = (function () {
    "use strict";

    var onUnknownCmd = function (cmdname, args, kwargs) {
        if (cmdname !== "vitals_update") return false;

        // Server sends as kwargs: oob=("vitals_update", {...})
        var data = (args && args[0]) || kwargs;
        if (!data) return true;

        updateBar("hp", data.hp, data.hp_max);
        updateBar("mana", data.mana, data.mana_max);
        updateBar("move", data.move, data.move_max);

        if (data.level !== undefined) {
            var levelEl = document.getElementById("vitals-level");
            if (levelEl) {
                levelEl.textContent = "Level " + data.level;
            }
        }

        return true;  // handled — suppress default_out error display
    };

    function updateBar(vitalName, current, max) {
        var container = document.getElementById("vital-" + vitalName);
        if (!container) return;

        var percent = max > 0 ? Math.round((current / max) * 100) : 0;
        percent = Math.max(0, Math.min(100, percent));

        var fill = container.querySelector(".bar-fill");
        var text = container.querySelector(".bar-text");

        if (fill) {
            fill.style.width = percent + "%";
            if (percent <= 25) {
                fill.style.backgroundColor = "#CC4444";
            } else if (percent <= 50) {
                fill.style.backgroundColor = "#DAA520";
            } else {
                fill.style.backgroundColor = "";
            }
        }
        if (text) {
            text.textContent = current + "/" + max;
        }
    }

    var init = function () {
        console.log("FCM Vitals Panel initialized.");
    };

    return {
        init: init,
        onUnknownCmd: onUnknownCmd,
    };
})();

plugin_handler.add("vitals_panel", vitals_panel_plugin);
