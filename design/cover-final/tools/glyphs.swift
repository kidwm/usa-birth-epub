import Foundation
import CoreText
import CoreGraphics

// Extract actual font outlines; no tracing of the AI proposal is involved.
let fontURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let descriptors = CTFontManagerCreateFontDescriptorsFromURL(fontURL as CFURL) as! [CTFontDescriptor]
let characters = Array("美國的誕生藍弋丰")
var output: [String: Any] = [:]
func n(_ value: CGFloat) -> String { String(format: "%.3f", Double(value)) }
for weight in [600, 900] {
    let variations = [NSNumber(value: 0x77676874): NSNumber(value: weight)]
    let descriptor = CTFontDescriptorCreateCopyWithAttributes(descriptors[0], [kCTFontVariationAttribute: variations] as CFDictionary)
    let font = CTFontCreateWithFontDescriptor(descriptor, 1000, nil)
    var glyphs: [String: Any] = [:]
    for character in characters {
        var utf16 = Array(String(character).utf16)
        var glyph = CGGlyph()
        precondition(CTFontGetGlyphsForCharacters(font, &utf16, &glyph, 1) && glyph != 0)
        let path = CTFontCreatePathForGlyph(font, glyph, nil)!
        var data = ""
        path.applyWithBlock { pointer in
            let element = pointer.pointee
            let p = element.points
            switch element.type {
            case .moveToPoint: data += "M\(n(p[0].x)),\(n(-p[0].y))"
            case .addLineToPoint: data += "L\(n(p[0].x)),\(n(-p[0].y))"
            case .addQuadCurveToPoint: data += "Q\(n(p[0].x)),\(n(-p[0].y)) \(n(p[1].x)),\(n(-p[1].y))"
            case .addCurveToPoint: data += "C\(n(p[0].x)),\(n(-p[0].y)) \(n(p[1].x)),\(n(-p[1].y)) \(n(p[2].x)),\(n(-p[2].y))"
            case .closeSubpath: data += "Z"
            @unknown default: fatalError("Unsupported path component")
            }
        }
        var advance = CGSize.zero
        CTFontGetAdvancesForGlyphs(font, .horizontal, &glyph, &advance, 1)
        glyphs[String(character)] = ["path":data,"advance":advance.width]
    }
    output[String(weight)] = ["postscript_name":CTFontCopyPostScriptName(font) as String,"glyphs":glyphs]
}
try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys]).write(to: outputURL)
print("Saved 8 glyphs at weights 600 and 900 to \(outputURL.path)")
