#pragma once

enum class FaceState {
    IDLE,
    STANDBY,
    LISTENING,
    THINKING,
    SPEAKING,
    ERROR_STATE
};

void display_init();
void display_set_state(FaceState state);
