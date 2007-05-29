" Reads the snipper file
pyfile ~/.vim/snipper/src/snipper.py

" maps the tab button to trigger snipper
imap <tab> <C-o>:python snipper.trigger()<CR>


"if you want to different buttons, one for expanding and one
"for jumping between the placeholders use these mappings instead
"and remove the snipper.trigger() map
"imap <tab> <C-o>:python snipper.expand()<CR>
"imap <F2> <C-o>:python snipper.jump()<CR>

"tries to read the filetype and load the correct template file
autocmd BufRead * python snipper.registerBuffer()
autocmd BufNewFile * python snipper.registerBuffer() 
