#version 140
// -*- mode: C -*-
// Defines emitted by gridrectst::init_gl at load:
// dimx, dimy:      Grid size of the screen array
// dispx, dispy:    Grid-cell (font) size
// vec4 colors[16]: Color palette; first non-bold, then bold

out vec4 gl_FragColor;

flat in vec4 frontColor;
flat in vec4 backColor;

smooth in vec2 texCoords;
uniform sampler2D textures;

void main() {
  vec4 texColor = texture2D(textures, texCoords);

  gl_FragColor = mix(backColor, frontColor * texColor, texColor.a);
}
