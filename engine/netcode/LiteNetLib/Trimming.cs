using System.Diagnostics.CodeAnalysis;

namespace LiteNetLib;

internal static class Trimming
{
	internal const DynamicallyAccessedMemberTypes SerializerMemberTypes = DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties;
}
