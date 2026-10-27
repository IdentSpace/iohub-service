from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from app.core.room import Room, RoomUtils

scheduler = BackgroundScheduler()


def start_scheduler():
	if scheduler.running:
		return
	rooms = RoomUtils.load_rooms()

	# TODO: await for x sec. (?)

	for room in rooms:
		scheduler.add_job(room.regulate_temperature, 'interval', seconds=900, id=f'temperature_control_{room.id}', replace_existing=True)
	
	scheduler.start()

def stop_scheduler():
	if scheduler.running:
		scheduler.shutdown(wait=False)
