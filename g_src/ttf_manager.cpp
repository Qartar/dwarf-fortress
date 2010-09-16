#include "ttf_manager.hpp"
#include "init.h"
#include <iostream>

using namespace std;

ttf_managerst ttf_manager;

bool ttf_managerst::init(int ceiling, int tile_width) {
  if (!::init.font.use_ttf) return false;
  
  // Reset to a known state, clear everything
  if ((!TTF_WasInit()) && (TTF_Init() == -1)) {
    MessageBox(NULL, TTF_GetError(), "TTF error", MB_OK);
    return false;
  }
  if (font) TTF_CloseFont(font);
  handles.clear();
  for (auto it = textures.cbegin(); it != textures.cend(); ++it)
    SDL_FreeSurface(it->second);
  textures.clear();
  this->tile_width = tile_width;
  this->ceiling = ceiling;
  // Try progressively smaller point sizes until we find one that fits
  for (int sz=20; sz > 0; sz--) {
    font = TTF_OpenFont("data/art/font.ttf", sz);
    if (!font) continue;
    if (TTF_FontHeight(font) <= ceiling) {
      cout << "Picked font at " << sz << " points for ceiling " << ceiling << endl;
#ifdef DEBUG
      // get the glyph metric for the letter 'g' in a loaded font
      cout << "TTF_FontHeight " << TTF_FontHeight(font) << endl;
      cout << "TTF_FontAscent " << TTF_FontAscent(font) << endl;
      cout << "TTF_FontDescent " << TTF_FontDescent(font) << endl;
      cout << "TTF_FontLineSkip " << TTF_FontLineSkip(font) << endl;
      int minx,maxx,miny,maxy,advance;
      if(TTF_GlyphMetrics(font,'g',&minx,&maxx,&miny,&maxy,&advance)==-1)
        printf("%s\n",TTF_GetError());
      else {
        printf("minx    : %d\n",minx);
        printf("maxx    : %d\n",maxx);
        printf("miny    : %d\n",miny);
        printf("maxy    : %d\n",maxy);
        printf("advance : %d\n",advance);
      }
#endif
      return true;
    }
    TTF_CloseFont(font);
  }
  // ..fine.
  cout << "No font found!" << endl;
  font = NULL;
  return false;
}

// Converts a TTF text width (in pixels) to an appropriate DF grid-tile width
int ttf_managerst::size_ttf(const string &text, int ttf_width) {
  int grid_width = (ttf_width + tile_width - 1) / tile_width;
  // We want to make sure the box width can be cleanly centered in the non-ttf box.
  return grid_width + ((text.size() - grid_width) % 2);
}

pair<int,int> ttf_managerst::get_handle(const ttf_id &text) {
  // Check for an existing handle
  auto it = handles.find(text);
  if (it != handles.end()) return it->second;
  // Right. Make a new one.
  int handle = ++max_handle;
  // Convert the passed in CP437 string to Unicode.
  vector<Uint16> text_unicode(text.text.length() + 1);
  int i;
  for (i=0; i < text.text.size(); i++)
    text_unicode[i] = charmap[text.text[i]];
  text_unicode[i] = 0;
  // Find the width
  int ttf_width, height;
  TTF_SizeUNICODE(font, &text_unicode[0], &ttf_width, &height);
  int width = size_ttf(text.text, ttf_width);
  // And insert.
  handles[text] = make_pair(handle, width);
  // We do the actual rendering in the render thread, later on.
  todo.push_back(make_pair(handle,text));
  return make_pair(handle,width);
}

SDL_Surface *ttf_managerst::get_texture(int handle) {
  // Run any outstanding renders
  if (!todo.empty()) {
    for (auto it = todo.cbegin(); it != todo.cend(); ++it) {
      const ttf_id &text = it->second;
      // First, convert the passed in CP437 string to Unicode.
      vector<Uint16> text_unicode(text.text.length() + 1);
      int i;
      for (i=0; i < text.text.size(); i++)
        text_unicode[i] = charmap[text.text[i]];
      text_unicode[i] = 0;
      // And then we can at last render
      // SDL_Color white = {255,255,255}, black = {0,0,0};
      const int fg = (text.fg + text.bold * 8) % 16;
      SDL_Color fgc = {Uint8(enabler.ccolor[fg][0]*255),
                       Uint8(enabler.ccolor[fg][1]*255),
                       Uint8(enabler.ccolor[fg][2]*255)};
      const int bg = text.bg % 16;

      SDL_Surface *textimg;
      if (text_unicode.size() <= 1) {
        // We need to special-case empty strings, as ttf_renderunicode segfaults on them.
        textimg = SDL_CreateRGBSurface(SDL_SWSURFACE, tile_width, ceiling, 32, 0, 0, 0, 0);
      } else {
        textimg = TTF_RenderUNICODE_Blended(font, &text_unicode[0], fgc);
      }
      // Finally, construct a box to render this in, and copy the text over
      SDL_Surface *box = SDL_CreateRGBSurface(SDL_SWSURFACE,
                                              size_ttf(text.text, textimg->w) * tile_width,
                                              ceiling,
                                              32, 0, 0, 0, 0);
      SDL_FillRect(box, NULL, SDL_MapRGB(box->format,
                                         Uint8(enabler.ccolor[bg][0]*255),
                                         Uint8(enabler.ccolor[bg][1]*255),
                                         Uint8(enabler.ccolor[bg][2]*255)));
      SDL_Rect dest = { text.justification == justify_center ? Sint16((box->w - textimg->w) / 2)
                        : text.justification == justify_right ? Sint16(box->w - textimg->w)
                        : Sint16(0),
                        0, 0, 0 };
      SDL_BlitSurface(textimg, NULL, box, &dest);
      if (text.text == " at any time for options, including key bindings.")
        SDL_SaveBMP(box, "foo.bmp");
      // ..and make it display format. Phew!
      SDL_Surface *box2 = SDL_DisplayFormat(box);
#ifdef DEBUG
      cout << "Rendering \"" << text.text << "\" at height " << box2->h << endl;
      cout << " width " << textimg->w << " in box of " << box->w << endl;
#endif
      SDL_FreeSurface(textimg);
      SDL_FreeSurface(box);
      // Store it for later.
      textures[it->first] = box2;
    }
    todo.clear();
  }
  // Find the li'l texture
  return textures[handle];
}
