" CUAUV Software Vim Configuration
" A minimal but convenient Vim configuration for viewing and quick editing.
"
" Tips:
" - Use H and L to move to beginning and end of line
" - Use gcc to comment the current line, or gc to comment the visual selection
" - Use either colon or semicolon for command mode
" - Use g<dir> like gh or gj to focus the left split or down split respectively

filetype plugin indent on

"
" Options
"

" Spaces
set tabstop=4       " Number of visual spaces per TAB
set softtabstop=4   " Number of spaces in tab when editing
set shiftwidth=4    " Number of spaces to use for autoindent
set expandtab       " Tabs are space
set autoindent
set copyindent      " Copy indent from the previous line

" UI
set termguicolors   " Enable true-color colorscheme support
set wildmenu        " Visual autocomplete for command menu
set cursorline	    " Highlight current line
set mouse=a         " Enable selecting with mouse
set splitbelow      " Open horizontal splits below current split
set splitright      " Open vertical splits to the right of current split
set hidden          " Okay to background modified buffers
set laststatus=2    " Window will always have a status line
set scrolloff=4	    " Leave lines visible at top and bottom of buffer
set noshowmode      " Annoying mode display, the cursor shows which mode we're in

" Searching
set ignorecase      " Case-insensitive
set smartcase       " Override ignorecase if search includes capital letters
set nohlsearch      " Don't highlight search after search is completed
set gdefault        " When using :s command, replace all instances on line by default

set clipboard=unnamedplus

" Swap/backup/undo
set noswapfile      " Disable concurrent editing warning, Vim warns when saving a modified file anyway
set undofile        " Enable persistent undo
let g:netrw_home='~/.local/share/nvim'  " Don't store history in vim config dir
 
" Load colorscheme
set background=dark
colorscheme space-vim-dark
syntax enable			" Enable syntax processing

"
" Mappings
"

" Leader
let mapleader = ","
let maplocalleader = "\\"

" Make Y behave like D and C, instead of like yy
nnoremap Y y$	

" Much better use of H and L
noremap H ^
noremap L $

" Allow using ; to access command mode in normal and visual mode
noremap ; :

" Splits: use g prefix instead of <C-w>
nnoremap gh <C-w>h
nnoremap gl <C-w>l
nnoremap gj <C-w>j
nnoremap gk <C-w>k
nnoremap gH <C-w>H
nnoremap gL <C-w>L
nnoremap gJ <C-w>J
nnoremap gK <C-w>K

" Easier tab manipulation / navigation
nnoremap <silent> <leader><tab> :tabnew<cr>
nnoremap <silent> <leader><s-tab> :tabc<cr>
nnoremap <silent> <tab> :tabn<cr>
nnoremap <silent> <s-tab> :tabp<cr>

nnoremap <leader><leader> :e#<cr> " Open last file

" Control-Backspace deletes last work in insert mode
noremap! <C-BS> <C-w>
noremap! <C-h> <C-w>

"
" Autocmd
"

" Jump to last cursor position in file
function! SetCursorPosition()
  if &filetype !~ 'svn\|commit\c'
    if line("'\"") > 0 && line("'\"") <= line("$") |
      execute 'normal! g`"zvzz' |
    endif
  end
endfunction

augroup restore_cursor
	autocmd!
	autocmd BufReadPost * call SetCursorPosition()
augroup END

" vim:shiftwidth=2
