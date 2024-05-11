# MediaSpinner

MediaSpinner is a Python script for playing collections of media at random, which was originally created for playing music at parties.

It takes a folder of media along with a configuration file, and allows for playback through a simple Web page.

## Requirements

* Python 3.7
* TCP port 8000 available on system (can be adjusted by editing the script)

## Setup

### Media Folder

The media folder must contain individual folders (collections) with media files. No other subfolders are supported.

For example:

```
media
├─collection1
│ ├─song1.mp3
│ └─song2.webm
└─collection2
  ├─song3.mp3
  ├─song4.ogg
  └─song5.ogg
```

### Configuration File

The configuration file controls which collections are played and how media is selected. For example:

```
{
	"collections": {
		"collection1": {
			"weight": 2
		},
		"collection2": {
			"backoff": 3
		},
	},
	"same_media_backoff": 10
}
```

* `collections`: Settings for each collection
	* `weight`: How likely an item is selected from this collection, relative to the other collections (default: 1)
	* `backoff`: How many items to wait before another item is played from the same collection (default: 0)
* `same_media_backoff`: How many items to wait before the same item is played again (default: 0)

In the example, media from the first collection will be played about twice as often as media from the second collection. There will be at least three other items between items from the second collection, and at least ten between two instances of the same item.

## Usage

Start the Web server with: `python3 mediaspinner.py [configuration file] [media folder]`

Load the Web page by opening: `http://localhost:8000/`

## API

MediaSpinner exposes a simple API you can use to build your own UI instead of using the one already provided.

### POST /playlist/next

Select the next media item.

Request body: Not used

Response body: JSON, containing the path to the next media item.

Example:

```
{
	"path": "collection1/song1.mp3"
}
```

### GET /media?path={path}

Retrieve a media file.

Parameters:

* `path`: Path to media file (from `/playlist/next`)

Response body: Raw media file

## License

MediaSpinner is available under the MIT License. Refer to `LICENSE.txt` for details.