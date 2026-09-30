import unittest
from unittest.mock import patch
from restoration_eval.room_runtime import navigation_query, room_html, install_room_navigation


class RoomRuntimeTests(unittest.TestCase):
    def test_each_room_accepts_only_its_own_query_namespace(self):
        for room,prefix in [('study_design','study_'),('metric_framework','metric_'),
                ('model_gallery','gallery_'),('stability_lab','stability_'),
                ('trustworthiness','trust_'),('focused_portrait_review','portrait_'),('case_explorer','ce_')]:
            query={'room':room,prefix+'selection':'exact-record'}
            self.assertEqual(navigation_query({'room':room,'query':query},room),query)
            self.assertIsNone(navigation_query({'room':room,'query':{**query,'wrong_key':'x'}},room))

    def test_transport_rejects_cross_room_and_malformed_values(self):
        self.assertIsNone(navigation_query({'room':'case_explorer','query':{'room':'trustworthiness'}},'case_explorer'))
        self.assertIsNone(navigation_query({'room':'case_explorer','query':{'room':'case_explorer','ce_layer':['bad']}},'case_explorer'))
        self.assertIsNone(navigation_query(None,'case_explorer'))

    def test_render_stamp_is_the_only_markup_change(self):
        original='<style>.room{color:red}</style><main class="ce-stage"><button>Original label</button></main><dialog>Original content</dialog>'
        with patch('restoration_eval.room_runtime.st.html') as render:
            revision=room_html(original)
        stamped=render.call_args.args[0]
        self.assertEqual(stamped.replace(f' data-room-render="{revision}"',''),original)

    def test_navigation_is_consumed_once_and_acknowledged(self):
        event={'id':'request-1','room':'case_explorer',
               'query':{'room':'case_explorer','ce_layer':'colour'}}
        with patch('restoration_eval.room_runtime.st') as streamlit, \
             patch('restoration_eval.room_runtime.components.declare_component') as declare:
            streamlit.session_state={}
            streamlit.query_params={'room':'case_explorer'}
            # A real QueryParams proxy supports both dict() and from_dict().
            class Query(dict):
                def from_dict(self, value):
                    self.clear()
                    self.update(value)
            streamlit.query_params=Query(streamlit.query_params)
            declare.return_value.return_value=event
            install_room_navigation('case_explorer')
            self.assertEqual(streamlit.query_params,event['query'])
            self.assertEqual(streamlit.session_state['_room_nav_ack'],'request-1')
            streamlit.rerun.assert_called_once()
            install_room_navigation('case_explorer')
            streamlit.rerun.assert_called_once()


if __name__=='__main__':
    unittest.main()
