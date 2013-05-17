import sublime, sublime_plugin

from collections import defaultdict
import heapq
import pickle
from functools import wraps

class ViewOrderChange(sublime_plugin.EventListener):

	def __init__(self):
		try:
			with open('.view_cache') as fd:
				self.view_hits = pickle.load(fd)
		except:
			self.view_hits = defaultdict(int)

		self.pending = set()
		self.sync_id = 0

	def writeback(self):
		self.sync_id += 1
		current_timeout = self.sync_id

		def callback():
			if current_timeout != self.sync_id:
				# Stale
				return

			with open('.view_cache', 'w') as fd:
				fd.write(pickle.dumps(self.view_hits))

		sublime.set_timeout(callback, 1000)

	def on_activated(self, view):
		self.pending.add(view.id())

	def on_close(self, view):
		self.pending.discard(view.id())

		for view_id, group in list(self.view_hits):
			if view.id() == view_id:
				del self.view_hits[(view_id, group)]
		
		self.writeback()

	def on_modified(self, view):
		# Only update once per activation, don't want to add to count every
		# modification!
		if view.id() not in self.pending:
			return

		self.pending.remove(view.id())
		window = view.window()

		group, _ = window.get_view_index(view)
		# Store view hits independently for each group.
		self.view_hits[(view.id(), group)] += 1

		views = window.views_in_group(group)
		view_heap = []

		for v in views:
			_, i = window.get_view_index(v)
			hits = self.view_hits[(v.id(), group)]
			if hits:
				# 10000 - i is a hack to keep original order.
				# i is the view index, take from 10000 to sort descending.
				heapq.heappush(view_heap, (hits, 10000-i, v))

		while view_heap:
			v = heapq.heappop(view_heap)[2]
			window.set_view_index(v, group, 0)

		window.focus_view(view)
		self.writeback()

	on_post_save = on_selection_modified = on_modified