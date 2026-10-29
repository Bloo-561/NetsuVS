extends Control
class_name InfoBar
## INFORMATION BAR
## The scrolling news ticker along the bottom of the title and menus
## (Persona 4 Arena style). Drop info_bar.tscn into any screen.
##
## Change the messages on each copy in the Inspector ("Messages").
## Change the colors in info_bar.tscn (InfoTab and TickerBox styles).

## Lines that scroll by, one after another. Add as many as you like.
@export var messages: PackedStringArray = [
	"Welcome to Netsu VS! A fighting game based on the Netsu no Kiseki campaign.",
	"Controls: A / B / C to attack, S to call your assist, Start to pause. Alt+Enter toggles fullscreen.",
	"Early build: expect placeholder art and plenty of bugs. Feedback is welcome!",
]
## How fast the text scrolls (pixels per second).
@export var speed: float = 200.0

@onready var ticker_box: Control = %TickerBox
@onready var ticker: Label = %Ticker

var _index := 0


func _ready() -> void:
	show_message(0)


func _process(delta: float) -> void:
	ticker.position.x -= speed * delta
	if ticker.position.x + ticker.size.x < 0.0:
		show_message(_index + 1)


## Jump to a message right away (starts from the right edge).
func show_message(index: int) -> void:
	if messages.is_empty():
		ticker.text = ""
		return
	_index = index % messages.size()
	ticker.text = messages[_index]
	ticker.size = Vector2.ZERO  # shrink to fit the new text
	ticker.position.x = ticker_box.size.x
