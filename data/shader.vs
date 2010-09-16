#version 140 // -*- mode: C -*-
// Defines emitted by gridrectst::init_gl at load:
// dimx, dimy:      Grid size of the screen array
// dispx, dispy:    Grid-cell (font) size
// vec4 colors[16]: Color palette; first non-bold, then bold
#ifdef GRAPHICS
// offset_texpos, offset_addcolor, offset_grayscale, offset_cf, offset_cbr:
//   offsets of the corresponding graphicst arrays in data
#endif

uniform usamplerBuffer data;
uniform samplerBuffer coords;
uniform isamplerBuffer fontmap;

uniform uint frame; // Counts up from 0

in vec4 gl_Vertex;
in int gl_VertexID;

flat out vec4 frontColor;
flat out vec4 backColor;
smooth out vec2 texCoords;

void main() {
  int tile = gl_VertexID / 6;
  int offset_tile = tile * 4;

  int ch   = int(texelFetch(data, offset_tile).a);
  int fg   = int(texelFetch(data, offset_tile+1).a);
  int bg   = int(texelFetch(data, offset_tile+2).a);
  int bold = clamp(int(texelFetch(data, offset_tile+3).a), 0, 1);

#ifdef GRAPHICS
  uint texpos = texelFetch(data, offset_texpos + offset_tile).a;
  texpos += texelFetch(data, offset_texpos + offset_tile + 1).a * 256u;
  texpos += texelFetch(data, offset_texpos + offset_tile + 2).a * 65536u;
  texpos += texelFetch(data, offset_texpos + offset_tile + 3).a * 16777216u;
  uint addcolor = texelFetch(data, offset_addcolor + offset_tile).a;
  uint grayscale = texelFetch(data, offset_grayscale + offset_tile).a;
  uint cf = texelFetch(data, offset_cf + offset_tile).a;
  uint cbr = texelFetch(data, offset_cbr + offset_tile).a;


  vec4 tex_square;
  if (texpos != 0u && ch != 0) {
    tex_square = texelFetch(coords, int(texpos));
    if (grayscale != 0u) {
      frontColor = colors[int(cf + cbr * 8u)];
    } else if (addcolor != 0u) {
      frontColor = colors[fg + bold * 8];
    } else {
      frontColor = vec4(1);
    }
  } else {
    tex_square = texelFetch(coords, texelFetch(fontmap, ch).a);
    frontColor  = colors[fg + bold * 8];
  }
#else
  vec4 tex_square = texelFetch(coords, texelFetch(fontmap, ch).a);
  frontColor  = colors[fg + bold * 8];
#endif

  vec2 coords[6] = vec2[](tex_square.sq, tex_square.tq, tex_square.tp,
                          tex_square.sq, tex_square.tp, tex_square.sp);
  texCoords = coords[gl_VertexID % 6];
  
  gl_Position = gl_Vertex;
  backColor   = colors[bg];
}
