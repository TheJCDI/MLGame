def execute(options):
	"""Start the game in the selected mode

	An additional game parameter (stored in options.game_params)
	for the game arkanoid is the level.

	@param options The game options specified in the command line
	"""
	try:
		level = int(options.game_params[0])
		if level < 1:
			raise ValueError
	except IndexError:
		print("Level is not specified. Set to 1.")
		level = 1
	except ValueError:
		print("Invalid level value. Set to 1.")
		level = 1

	if options.manual_mode:
		_manual_mode(options.fps, level, options.record_progress)
	else:
		_ml_mode(options.fps, level, options.input_script[0], \
			options.record_progress, options.one_shot_mode)

def _ml_mode(fps, level, input_script = "ml_play_template.py", \
	record_progress = False, one_shot_mode = False):
	"""Start the game in the machine learning mode

	Create a game and a machine learning processes, and pipes for communicating.
	The main process is the drawing process, which will draw the game progress
	according to the information sent from the game process.

	After quit from the drawing loop,
	the created processes will be terminated.

	@param fps Specify the updating rate of the game
	@param level Specify the level of the game
	@param input_script Specify the script for the ml process
	@param record_progress Specify whether to record the game progress or not
	@param one_shot_mode Specify whether to run the game only once or not
	"""

	from multiprocessing import Process, Pipe

	instruct_pipe_r, instruct_pipe_s = Pipe(False)
	scene_info_pipe_r, scene_info_pipe_s = Pipe(False)

	ml_process = Process(target = _start_ml_process, name = "ml process", \
		args = (input_script, instruct_pipe_s, scene_info_pipe_r))

	ml_process.start()

	_start_game_process(fps, level, record_progress, one_shot_mode, \
		instruct_pipe_r, scene_info_pipe_s)

	ml_process.terminate()

def _start_game_process(fps, level, record_progress, one_shot_mode, \
	instruct_pipe, scene_info_pipe):
	"""Start the game process

	@param fps Specify the updating rate of the game
	@param level Specify the level of the game
	@param record_progress Whether to record the game progress
	@param one_shot_mode Whether to run the game for only one round
	@param instruct_pipe The pipe for receiving the instruction from the ml process
	@param scene_info_pipe The pipe for sending the scene info to the ml process
	"""
	from .game.arkanoid_ml import Arkanoid
	try:
		record_handler = _get_record_handler(record_progress)
		game = Arkanoid(fps, level, record_handler, one_shot_mode)
		game.game_loop(instruct_pipe, scene_info_pipe)
	except RuntimeError as e:
		print(e)
	except Exception as e:
		import traceback
		from essential.exception import ExceptionMessage
		exception_msg = ExceptionMessage("game", traceback.format_exc())
		print("Exception occurred in the {} process:" \
				.format(exception_msg.process_name))
		print(exception_msg.exc_msg)

def _start_ml_process(target_script, instruct_pipe, scene_info_pipe):
	"""Start the custom machine learning process

	@param target_script Specify the name of the script to be used.
	       The Script must have function `ml_loop()` and be put in the "ml"
	       directory of the game.
	@param instruct_pipe The sending-end of pipe for the game instruction
	@param scene_info_pipe The receiving-end of pipe for the scene information
	"""
	# Initialize the pipe for helper functions in communication.py
	from . import communication as comm
	comm._instruct_pipe = instruct_pipe
	comm._scene_info_pipe = scene_info_pipe

	try:
		script_name = target_script.split('.')[0]

		import importlib
		ml = importlib.import_module(".ml.{}".format(script_name), __package__)
		ml.ml_loop()
	except Exception as e:
		import traceback
		from essential.exception import ExceptionMessage, trim_callstack
		trimmed_callstack = trim_callstack(traceback.format_exc(), target_script)
		exc_msg = ExceptionMessage("ml", trimmed_callstack)
		comm._instruct_pipe.send(exc_msg)

def _manual_mode(fps, level, record_progress = False):
	"""Play the game as a normal game

	@param fps Specify the updating rate of the game
	@param level Specify the level of the game
	@param record_progress Specify whether to record the game progress or not
	"""
	from .game.arkanoid import Arkanoid

	record_handler = _get_record_handler(record_progress)
	game = Arkanoid(fps, level, record_handler)
	game.game_loop()

def _get_record_handler(record_progress: bool):
	"""Return the handler for record the game progress

	If the `record_progress` is False, return a dummy function.
	"""
	if record_progress:
		from essential.recorder import Recorder
		from .game import gamecore
		recorder = Recorder( \
			(gamecore.GAME_OVER_MSG, gamecore.GAME_PASS_MSG), \
			_get_log_dir_path())
		return recorder.record_scene_info
	else:
		return lambda x: None

def _get_log_dir_path():
	import os.path
	dirpath = os.path.dirname(__file__)
	return os.path.join(dirpath, "log")
