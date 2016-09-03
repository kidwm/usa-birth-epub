#!/bin/bash
rm "$1"
zip -X0 "$1" mimetype
zip -X9r "$1" META-INF EPUB -x "*.DS_Store"
