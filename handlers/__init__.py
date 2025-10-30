"""Handlers package"""
from handlers.start import start_handler, main_menu_callback, onboarding_complete
from handlers.people import (
    people_menu_callback,
    people_add_callback,
    people_list_callback,
    people_view_callback,
    people_delete_callback,
    people_delete_confirm_callback,
    handle_person_photo,
    done_adding_person,
    handle_person_name
)
from handlers.filter import (
    filter_people_callback,
    handle_filter_photo
)
from handlers.improve_model import (
    ask_improve_model,
    improve_model_declined,
    improve_model_accepted,
    confirm_face_callback
)
from handlers.events import (
    create_event_callback,
    enter_event_code_callback,
    event_status_callback,
    event_more_callback,
    event_stop_callback,
    copy_event_callback,
    handle_event_zip,
    handle_event_code_input
)

__all__ = [
    'start_handler',
    'main_menu_callback',
    'onboarding_complete',
    'people_menu_callback',
    'people_add_callback',
    'people_list_callback',
    'people_view_callback',
    'people_delete_callback',
    'people_delete_confirm_callback',
    'handle_person_photo',
    'done_adding_person',
    'handle_person_name',
    'filter_people_callback',
    'handle_filter_photo',
    'ask_improve_model',
    'improve_model_declined',
    'improve_model_accepted',
    'confirm_face_callback',
    'create_event_callback',
    'enter_event_code_callback',
    'event_status_callback',
    'event_more_callback',
    'event_stop_callback',
    'copy_event_callback',
    'handle_event_zip',
    'handle_event_code_input',
]
