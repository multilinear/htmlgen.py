#!/bin/bash
title=$(date +"%Y-%m-%dT%H:%M:%S%z")_"${1}".blog
echo "Creating file \"${title}\""
touch "${title}"
${EDITOR} "${title}"
