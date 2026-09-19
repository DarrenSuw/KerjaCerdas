using System;
using System.Runtime.InteropServices;

public class CredentialReader
{
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool CredRead(string target, int type, int reservedFlag, out IntPtr credentialPtr);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool CredFree(IntPtr buffer);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct CREDENTIAL
    {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public long LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    public static void Main()
    {
        IntPtr credPtr;
        // 1 = CRED_TYPE_GENERIC
        if (CredRead("git:https://github.com", 1, 0, out credPtr))
        {
            try
            {
                var cred = (CREDENTIAL)Marshal.PtrToStructure(credPtr, typeof(CREDENTIAL));
                byte[] blob = new byte[cred.CredentialBlobSize];
                Marshal.Copy(cred.CredentialBlob, blob, 0, cred.CredentialBlobSize);
                // Blob is UTF-16 LE
                string password = System.Text.Encoding.Unicode.GetString(blob);
                Console.WriteLine(password);
            }
            finally
            {
                CredFree(credPtr);
            }
        }
        else
        {
            Console.WriteLine("Could not read credential. Error: " + Marshal.GetLastWin32Error());
        }
    }
}
