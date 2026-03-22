"""
Weather description strings for room display and broadcast messages.

Three tiers of weather exposure:
- EXPOSED: full weather description appended to room desc
- SHELTERED: muffled indoor sounds (only for audible weather)
- SUBTERRANEAN: nothing
"""

from enums.weather import Weather


# ================================================================== #
#  Room description lines — appended to room desc on look
# ================================================================== #

# Exposed (outdoor) rooms — full weather descriptions
EXPOSED_WEATHER_DESCS = {
    Weather.CLOUDY: "|xGrey clouds blanket the sky overhead.|n",
    Weather.RAIN: "|bRain falls steadily, soaking the ground.|n",
    Weather.STORM: "|!|[B|wLightning flashes and thunder rolls across the sky.|n",
    Weather.SNOW: "|wSnow falls softly, blanketing the ground in white.|n",
    Weather.FOG: "|xA thick fog clings to the ground, limiting visibility.|n",
    Weather.BLIZZARD: "|!|[w|xDriving snow and howling wind reduce visibility to nothing.|n",
    Weather.HEAT_WAVE: "|YThe air is oppressively hot, shimmering with heat haze.|n",
    # CLEAR: no line (omitted intentionally)
}

# Sheltered (indoor/building) rooms — muffled sounds only
SHELTERED_WEATHER_DESCS = {
    Weather.RAIN: "|xThe steady patter of rain sounds against the roof.|n",
    Weather.STORM: "|xThunder rumbles outside, muffled by the walls.|n",
    Weather.BLIZZARD: "|xThe wind howls outside, and you can hear snow battering the walls.|n",
    # Other weather types: not audible indoors (omitted intentionally)
}


# ================================================================== #
#  Broadcast transition messages — sent when weather changes
# ================================================================== #

# Exposed rooms get these
TRANSITION_MESSAGES = {
    Weather.CLEAR: "|YThe clouds part and the sky clears.|n",
    Weather.CLOUDY: "|xClouds gather overhead, dimming the light.|n",
    Weather.RAIN: "|bRain begins to fall, pattering against the ground.|n",
    Weather.STORM: "|!|[B|wThunder cracks as a storm rolls in!|n",
    Weather.SNOW: "|wSnowflakes begin to drift down from the grey sky.|n",
    Weather.FOG: "|xA thick fog rolls in, obscuring your surroundings.|n",
    Weather.BLIZZARD: "|!|[w|xA howling blizzard descends, wind driving snow in blinding sheets!|n",
    Weather.HEAT_WAVE: "|!|[W|rThe air shimmers with oppressive heat.|n",
}

# Sheltered rooms get muffled variants (only for audible weather)
SHELTERED_TRANSITION_MESSAGES = {
    Weather.RAIN: "|xYou hear the patter of rain against the roof.|n",
    Weather.STORM: "|xYou hear thunder rumbling outside.|n",
    Weather.BLIZZARD: "|xThe wind howls outside, rattling the walls.|n",
}
