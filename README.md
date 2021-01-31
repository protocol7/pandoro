# Pandoro

The love child of Trello and Pomodoro.

Pandoro is a [Bitbar](https://github.com/matryer/bitbar) plugin that provides a
Pomodoro timer, backed by Trello for todos. It is highly tuned for my workflow.
For something more fully featured, take a look at [Pomello](https://pomelloapp.com/).

To use, simply [install](https://github.com/matryer/bitbar#installing-plugins)
`pandoro.1s.py` among your Bitbar plugins. You need Python 3 and Requests installed.
Lastly, create a config file at `~/.pandororc` containing:

```javascript
{
    "key": "<your Trello API key>",
    "token": "< Trello API token>",
    "todo-list": "<Your Trello Todo list ID>",
    "done-list": "<Your Trello Done list ID>"
}
```

Get your Trello API key and token as described
[here](https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/).

To get the list IDs, you can use the Trello API, or the `lists.py` script. To run
`lists.py` you first need to add your key and token to the config file, and then run:

```sh
./lists.py <Your board slug>
```

For example:

```sh
./lists.py 2rdyTVWx
```