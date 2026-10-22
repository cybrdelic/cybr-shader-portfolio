import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest import mock
spec=importlib.util.spec_from_file_location("restore",Path(__file__).resolve().parents[1]/"restore_assets.py")
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)
def digest(data):return hashlib.sha256(data).hexdigest()
class RestoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
  self.data=b"verified source cache"*20;self.part=self.root/"part";self.part.write_bytes(self.data);self.target=self.root/"cache.bin";self.manifest=self.root/"manifest.json"
  self.manifest.write_text(json.dumps({"schema":"lossless-cache-transport/v1","files":[{"path":"cache.bin","bytes":len(self.data),"sha256":digest(self.data),"parts":[{"path":"part","bytes":len(self.data),"sha256":digest(self.data)}]}]}))
  for key,value in [("ROOT",self.root),("MANIFEST",self.manifest)]:
   patch=mock.patch.object(restore,key,value);patch.start();self.addCleanup(patch.stop)
 def test_restores_and_is_idempotent(self):
  restore.restore();self.assertEqual(self.target.read_bytes(),self.data);before=self.target.stat().st_mtime_ns;restore.restore();self.assertEqual(before,self.target.stat().st_mtime_ns)
 def test_preserves_different_existing_file(self):
  self.target.write_bytes(b"owned")
  with self.assertRaises(FileExistsError):restore.restore()
  self.assertEqual(self.target.read_bytes(),b"owned")
 def test_rejects_corrupt_part_without_output(self):
  self.part.write_bytes(b"corrupt")
  with self.assertRaises(ValueError):restore.restore()
  self.assertFalse(self.target.exists())
 def test_rejects_escape_path(self):
  with self.assertRaises(ValueError):restore.local_path("../escape")
 def test_access_denied_is_not_hidden(self):
  error=OSError("denied");error.winerror=5
  with mock.patch.object(restore.os,"link",side_effect=error),mock.patch.object(restore.os,"rename") as rename:
   with self.assertRaises(OSError):restore.restore()
   rename.assert_not_called()
 @unittest.skipUnless(os.name=="nt","Windows no-overwrite rename")
 def test_unsupported_link_race_preserves_winner(self):
  def race(source,target):
   self.target.write_bytes(b"winner");e=OSError("unsupported");e.winerror=1;raise e
  with mock.patch.object(restore.os,"link",side_effect=race):
   with self.assertRaises(FileExistsError):restore.restore()
  self.assertEqual(self.target.read_bytes(),b"winner");self.assertFalse(list(self.root.glob(".*.restore-*")))
if __name__=="__main__":unittest.main()
