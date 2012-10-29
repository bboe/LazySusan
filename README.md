LazySusan is a pluginable bot for turntable.fm. She's currently in her early
stages of development, so her plugin API could change.

## Setup

0. Install the package

        pip install lazysusan

0. Copy `lazysusan-sample.ini` to `lazysusan.ini`.

0. Update lazysusan.ini to include your connection information as per [these
instructions](http://alaingilbert.github.com/Turntable-API/bookmarklet.html).

0. Launch lazysusan

        lazysusan


## Specifying Additional Configuration Sections

In your `lazysusan.ini` you can add additional configuration sections and
select one of those selections when you start lazysusan. Say for example you
want to only load the `echo` plugin. You might define the following section:

```
[echo_only]
plugins: simple.Echo
```

Then launch lazysusan via:

    lazysusan -c echo_only



## Writing Your Own Plugins

Here we will describe how to write the plugins `sample.Sample` and
`sample.CommandSample`.

#### Create the file sample.py.

You can save this file in any directory, just remember the path to the file.

#### Copy the following contents into the file:

```python
from lazysusan.plugins import CommandPlugin, Plugin


class Sample(Plugin):
    """A plugin that outputs information about the songs that begin playing."""
    def __init__(self, *args, **kwargs):
        super(Sample, self).__init__(*args, **kwargs)
        print('Sample loaded!')
        self.register('newsong', self.handle_newsong)

    def handle_newsong(self, data):
        song_info = data['room']['metadata']['current_song']
        print('{0} started playing playing "{1}" by {2}'
              .format(song_info['djname'], song_info['metadata']['song'],
                      song_info['metadata']['artist']))


class CommandSample(CommandPlugin):
    """A plugin to demonstrate how to create commands."""
    COMMANDS = {'/test': 'test'}

    def __init__(self, *args, **kwargs):
        super(CommandSample, self).__init__(*args, **kwargs)
        print('CommandSample loaded!')

    def test(self, message, data):
        """The help message for the command /test."""
        print('The test command was called')
```

#### Update your lazysusan.ini to indicate you want to load your new plugins:

```
plugins: sample.Sample
         sample.CommandSample
```

#### Run lazysusan and specify the directory containing your plugins:

    lazysusan -p /path/to/plugin/directory

#### Join the room the bot is running in and verify the plugins work:

First send the message `/commands` to the bot via pm (or room chat) and verify
that `/test` is included in the list.

Then send `/test` and notice that the message `The test command was called`
should appear in your terminal.

Finally you should see messages in your terminal when new songs start playing.