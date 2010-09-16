#ifndef TTF_MANAGER_HPP
#define TTF_MANAGER_HPP

#include "enabler.h"
#include <SDL/SDL_ttf.h>
#include <unordered_map>

using std::unordered_map;

class ttf_managerst {
  TTF_Font *font;
  int max_handle;
  int tile_width, ceiling;
  unordered_map<ttf_id, pair<int,int> > handles; // First is handle, second is width
  unordered_map<int, SDL_Surface*> textures;
  list<pair<int,ttf_id> > todo;
  int size_ttf(const string &text, int);
public:
  ttf_managerst() {
    font = NULL;
    max_handle = 1;
  }
  bool init(int ceiling, int tile_width);
  bool was_init() { return font != NULL; }
  // Returns a handle for some TTF text (first), plus its onscreen width (second)
  pair<int,int> get_handle(const ttf_id &id);
  // Returns rendered text. Renders too, if necessary.
  // The returned SDL_Surface is owned by the ttf_managerst.
  SDL_Surface *get_texture(int handle);
};

extern ttf_managerst ttf_manager;

#endif
