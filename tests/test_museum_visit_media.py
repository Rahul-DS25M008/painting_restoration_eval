"""Checks for the optional tour film's pinned Streamlit media adapter."""
import unittest
from unittest.mock import Mock, patch
from restoration_eval import museum_visit


class TourMediaTests(unittest.TestCase):
    def test_no_runtime_is_safe(self):
        with patch.object(museum_visit.runtime, 'exists', return_value=False):
            self.assertIsNone(museum_visit.tour_media())

    def test_registers_same_origin_files_each_session(self):
        manager = Mock()
        manager.add.side_effect = ['/media/film.mp4', '/media/poster.jpg'] * 2
        with patch.object(museum_visit.runtime, 'exists', return_value=True), patch.object(
            museum_visit.runtime, 'get_instance', return_value=Mock(media_file_mgr=manager)
        ):
            for _ in range(2):
                self.assertEqual(museum_visit.tour_media(), {'video': '/media/film.mp4', 'poster': '/media/poster.jpg', 'duration': 115})
        self.assertEqual(manager.add.call_count, 4)
        self.assertEqual(manager.add.call_args_list[0].args[1:], ('video/mp4', 'museum-visit.video'))
        self.assertEqual(manager.add.call_args_list[1].args[1:], ('image/jpeg', 'museum-visit.poster'))

    def test_media_failure_does_not_break_the_route(self):
        with patch.object(museum_visit.runtime, 'exists', return_value=True), patch.object(
            museum_visit.runtime, 'get_instance', side_effect=RuntimeError('unavailable')
        ), self.assertLogs(museum_visit.__name__, level='ERROR'):
            self.assertIsNone(museum_visit.tour_media())

    def test_other_rooms_do_not_load_the_film(self):
        with patch.object(museum_visit, 'tour_media') as media, patch.object(museum_visit.components, 'html') as render:
            museum_visit.render_museum_visit('study_design')
        media.assert_not_called()
        self.assertIn('"media": null', render.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
