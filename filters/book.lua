-- Keep the manuscript independent of EPUB markup and presentation labels.
local roman = { 'Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ' }

function Header(h)
  local part = h.identifier:match('^part(%d+)$')
  local chapter = h.identifier:match('^chapter(%d+)$')
  local kind, label
  if part then
    kind, label = 'part', roman[tonumber(part)] or part
  elseif chapter then
    kind, label = 'chapter', '第 ' .. tostring(tonumber(chapter)) .. ' 章'
  elseif h.identifier == 'afterword' then
    kind, label = 'afterword', '美國的誕生・終章'
  elseif h.identifier == 'colophon' then
    h.attributes['epub:type'] = 'copyright-page'
    h.classes:insert('colophon')
  end
  if kind then
    h.classes:insert(kind)
    h.attributes['epub:type'] = kind
    h.content = {
      pandoc.Span({pandoc.Str(label)}, pandoc.Attr('', {'division-label'})),
      pandoc.Space(),
      pandoc.Span(h.content, pandoc.Attr('', {'division-title'}))
    }
  end
  return h
end
